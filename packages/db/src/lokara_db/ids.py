"""String primary keys. docs/02 allows cuid or uuid — uuid4 needs no dependency."""

import uuid


def new_id() -> str:
    return str(uuid.uuid4())
