export function InactivePhotoSlot() {
  return (
    <section aria-labelledby="inactive-photo-title" aria-disabled="true" className="space-y-2">
      <h3 id="inactive-photo-title" className="font-display font-semibold text-ink">
        Fotos (optional)
      </h3>
      <div className="rounded-xl border border-dashed border-slate/50 bg-mint/40 p-4 text-center text-slate">
        <div className="flex min-h-24 items-center justify-center rounded-lg bg-mint">
          <span className="font-semibold">Foto folgt</span>
        </div>
        <p className="mt-3 font-semibold text-ink">Foto-Upload kommt bald</p>
        <p className="mt-1 text-sm">Wird in einer späteren Version aktiviert.</p>
      </div>
    </section>
  );
}
