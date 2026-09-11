"""Immutable publication of archived documents to the renter portal."""

from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Response, status
from lokara_db import (
    RenterDeliveryArtifact,
    RenterPortalPublication,
    Statement,
    StatementArchive,
    StatementStatus,
    UviDeliveryEvent,
    new_id,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..authorization import portal_membership_id, require_owner
from ..deps import PathAccountSession, PathRenterSession
from ..schemas import (
    RenterPortalPublicationCreate,
    RenterPortalPublicationList,
    RenterPortalPublicationOut,
)

router = APIRouter()


def _publication_out(row: RenterPortalPublication) -> RenterPortalPublicationOut:
    return RenterPortalPublicationOut(
        id=row.id,
        tenancy_id=row.tenancy_id,
        source_kind=cast(Literal["STATEMENT_ARCHIVE", "UVI_ARTIFACT"], row.source_kind),
        document_type=cast(
            Literal["COVER_LETTER", "TENANT_STATEMENT", "UVI"],
            row.document_type,
        ),
        filename=row.filename,
        mime_type=row.mime_type,
        sha256=row.sha256,
        published_at=row.published_at,
        supersedes_publication_id=row.supersedes_publication_id,
        download_url=f"/renter/{row.tenancy_id}/documents/{row.id}/download",
    )


def _existing_publication(
    session: PathAccountSession,
    *,
    account_id: str,
    statement_archive_id: str | None,
    renter_delivery_artifact_id: str | None,
) -> RenterPortalPublication | None:
    query = select(RenterPortalPublication).where(RenterPortalPublication.account_id == account_id)
    if statement_archive_id is not None:
        query = query.where(RenterPortalPublication.statement_archive_id == statement_archive_id)
    else:
        query = query.where(
            RenterPortalPublication.renter_delivery_artifact_id == renter_delivery_artifact_id
        )
    return session.scalar(query)


def _idempotent_result(
    existing: RenterPortalPublication,
    body: RenterPortalPublicationCreate,
    response: Response,
) -> RenterPortalPublicationOut:
    if (
        existing.tenancy_id != body.tenancy_id
        or existing.supersedes_publication_id != body.supersedes_publication_id
    ):
        raise HTTPException(
            status_code=409,
            detail="Diese Dokumentquelle wurde bereits anders veröffentlicht.",
        )
    response.status_code = status.HTTP_200_OK
    return _publication_out(existing)


def _statement_source(
    session: PathAccountSession,
    *,
    source_id: str,
    tenancy_id: str,
) -> tuple[StatementArchive, Literal["COVER_LETTER", "TENANT_STATEMENT"]]:
    source = session.get(StatementArchive, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Dokumentquelle nicht gefunden.")
    if source.audience != "TENANT" or source.document_type not in {
        "COVER_LETTER",
        "TENANT_STATEMENT",
    }:
        raise HTTPException(status_code=422, detail="Dokumentquelle ist nicht veröffentlichbar.")
    if source.tenancy_id != tenancy_id:
        raise HTTPException(status_code=404, detail="Dokumentquelle nicht gefunden.")

    statement = session.get(Statement, source.statement_id)
    snapshot = None if statement is None else statement.finalized_snapshot
    blockers = snapshot.get("production_blockers") if isinstance(snapshot, dict) else None
    if (
        statement is None
        or statement.status not in {StatementStatus.FINALIZED, StatementStatus.SUPERSEDED}
        or statement.finalized_at is None
        or not isinstance(blockers, list)
        or blockers
    ):
        raise HTTPException(status_code=422, detail="Dokumentquelle ist nicht veröffentlichbar.")
    if not compare_digest(sha256(source.content_bytes).hexdigest(), source.sha256):
        raise HTTPException(status_code=422, detail="Dokumentquelle ist beschädigt.")
    return source, cast(Literal["COVER_LETTER", "TENANT_STATEMENT"], source.document_type)


def _uvi_source(
    session: PathAccountSession,
    *,
    source_id: str,
    tenancy_id: str,
) -> RenterDeliveryArtifact:
    source = session.get(RenterDeliveryArtifact, source_id)
    if source is None or source.tenancy_id != tenancy_id:
        raise HTTPException(status_code=404, detail="Dokumentquelle nicht gefunden.")
    if (
        source.artifact_kind != "UVI"
        or source.uvi_run_id is None
        or not isinstance(source.production_blockers_snapshot, list)
        or source.production_blockers_snapshot
    ):
        raise HTTPException(status_code=422, detail="Dokumentquelle ist nicht veröffentlichbar.")
    if not compare_digest(sha256(source.content_bytes).hexdigest(), source.sha256):
        raise HTTPException(status_code=422, detail="Dokumentquelle ist beschädigt.")
    return source


def _verify_predecessor(
    session: PathAccountSession,
    *,
    account_id: str,
    tenancy_id: str,
    document_type: str,
    predecessor_id: str | None,
) -> None:
    if predecessor_id is None:
        return
    predecessor = session.scalar(
        select(RenterPortalPublication).where(
            RenterPortalPublication.id == predecessor_id,
            RenterPortalPublication.account_id == account_id,
        )
    )
    if predecessor is None:
        raise HTTPException(status_code=404, detail="Vorgängerdokument nicht gefunden.")
    if predecessor.tenancy_id != tenancy_id or predecessor.document_type != document_type:
        raise HTTPException(
            status_code=422,
            detail="Vorgängerdokument gehört nicht zu diesem Dokumentstrom.",
        )


@router.post(
    "/a/{account_id}/renter-portal-publications",
    response_model=RenterPortalPublicationOut,
    status_code=status.HTTP_201_CREATED,
)
def publish_renter_document(
    account_id: str,
    body: RenterPortalPublicationCreate,
    response: Response,
    session: PathAccountSession,
) -> RenterPortalPublicationOut:
    require_owner(session)

    existing = _existing_publication(
        session,
        account_id=account_id,
        statement_archive_id=body.statement_archive_id,
        renter_delivery_artifact_id=body.renter_delivery_artifact_id,
    )
    if existing is not None:
        return _idempotent_result(existing, body, response)

    statement_source: StatementArchive | None = None
    uvi_source: RenterDeliveryArtifact | None = None
    source_kind: Literal["STATEMENT_ARCHIVE", "UVI_ARTIFACT"]
    document_type: Literal["COVER_LETTER", "TENANT_STATEMENT", "UVI"]
    if body.statement_archive_id is not None:
        statement_source, statement_document_type = _statement_source(
            session,
            source_id=body.statement_archive_id,
            tenancy_id=body.tenancy_id,
        )
        source_kind = "STATEMENT_ARCHIVE"
        document_type = statement_document_type
        content_bytes = statement_source.content_bytes
        source_digest = statement_source.sha256
        mime_type = statement_source.mime_type
        filename = statement_source.filename
    else:
        assert body.renter_delivery_artifact_id is not None
        uvi_source = _uvi_source(
            session,
            source_id=body.renter_delivery_artifact_id,
            tenancy_id=body.tenancy_id,
        )
        source_kind = "UVI_ARTIFACT"
        document_type = "UVI"
        content_bytes = uvi_source.content_bytes
        source_digest = uvi_source.sha256
        mime_type = uvi_source.mime_type
        filename = uvi_source.filename

    _verify_predecessor(
        session,
        account_id=account_id,
        tenancy_id=body.tenancy_id,
        document_type=document_type,
        predecessor_id=body.supersedes_publication_id,
    )

    publication = RenterPortalPublication(
        id=new_id(),
        account_id=account_id,
        tenancy_id=body.tenancy_id,
        source_kind=source_kind,
        statement_archive_id=body.statement_archive_id,
        renter_delivery_artifact_id=body.renter_delivery_artifact_id,
        document_type=document_type,
        content_bytes=content_bytes,
        sha256=source_digest,
        mime_type=mime_type,
        filename=filename,
        published_by_membership_id=portal_membership_id(session),
        published_at=datetime.now(UTC),
        supersedes_publication_id=body.supersedes_publication_id,
    )
    try:
        with session.begin_nested():
            session.add(publication)
            session.flush()
            if uvi_source is not None:
                assert uvi_source.uvi_run_id is not None
                session.add(
                    UviDeliveryEvent(
                        id=new_id(),
                        account_id=account_id,
                        uvi_run_id=uvi_source.uvi_run_id,
                        status="PUBLISHED",
                        occurred_at=publication.published_at,
                    )
                )
                session.flush()
    except IntegrityError as exc:
        existing = _existing_publication(
            session,
            account_id=account_id,
            statement_archive_id=body.statement_archive_id,
            renter_delivery_artifact_id=body.renter_delivery_artifact_id,
        )
        if existing is not None:
            return _idempotent_result(existing, body, response)
        raise HTTPException(
            status_code=409,
            detail="Das Dokument konnte nicht veröffentlicht werden.",
        ) from exc

    return _publication_out(publication)


@router.get(
    "/renter/{tenancy_id}/documents",
    response_model=RenterPortalPublicationList,
)
def list_renter_documents(
    tenancy_id: str,
    session: PathRenterSession,
) -> RenterPortalPublicationList:
    rows = session.scalars(
        select(RenterPortalPublication)
        .where(RenterPortalPublication.tenancy_id == tenancy_id)
        .order_by(
            RenterPortalPublication.published_at.asc(),
            RenterPortalPublication.id.asc(),
        )
    ).all()
    return RenterPortalPublicationList(documents=[_publication_out(row) for row in rows])


@router.get("/renter/{tenancy_id}/documents/{publication_id}/download")
def download_renter_document(
    tenancy_id: str,
    publication_id: str,
    session: PathRenterSession,
) -> Response:
    row = session.scalar(
        select(RenterPortalPublication).where(
            RenterPortalPublication.id == publication_id,
            RenterPortalPublication.tenancy_id == tenancy_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden.")

    digest = sha256(row.content_bytes).hexdigest()
    if not compare_digest(digest, row.sha256):
        raise HTTPException(
            status_code=409, detail="Dokumentintegrität konnte nicht bestätigt werden."
        )

    return Response(
        content=row.content_bytes,
        media_type=row.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{row.filename}"',
            "X-Content-SHA256": row.sha256,
        },
    )
