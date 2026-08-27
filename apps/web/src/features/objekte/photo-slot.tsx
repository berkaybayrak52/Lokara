/**
 * Bild-Slot (Spec 02-objekte, O12): sichtbar, aber INAKTIV. Es gibt heute keinen
 * Objekt-/Dateispeicher, daher kein `<input type=file>`, kein Upload-Request und
 * keine externe Bild-URL — nur ein ehrlicher Platzhalter „Foto folgt / kommt bald".
 */
export function PhotoSlot() {
  return (
    <div className="mt-2">
      <p className="text-sm font-medium text-ink">Fotos (optional)</p>
      <div className="mt-2 flex items-center gap-4 rounded-xl border border-dashed border-mint bg-mint/40 p-4 opacity-70">
        <div className="flex h-16 w-24 shrink-0 items-center justify-center rounded-lg bg-mint text-xs text-slate">
          Foto folgt
        </div>
        <div>
          <p className="text-sm font-medium text-slate">Foto-Upload kommt bald</p>
          <p className="text-xs text-slate">Wird in einer späteren Version aktiviert.</p>
        </div>
      </div>
    </div>
  );
}
