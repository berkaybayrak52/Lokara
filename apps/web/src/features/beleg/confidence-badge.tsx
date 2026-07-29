/**
 * How sure the extraction is about one field.
 *
 * Never colour alone (BFSG): the percentage is always spelled out, and a field
 * that needs a human carries a triangle glyph AND the word "prüfen" — the
 * tint is the third signal, not the only one.
 */
export function ConfidenceBadge({
  percent,
  needsReview,
}: {
  percent: number;
  needsReview: boolean;
}) {
  const className = needsReview
    ? 'bg-warning-tint text-warning'
    : 'bg-mint/70 text-ink';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold tabular-nums ${className}`}
    >
      {needsReview ? (
        <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true" className="size-3.5">
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M8.68 3.03c.6-1.04 2.04-1.04 2.64 0l6.7 11.6c.58 1-.16 2.24-1.32 2.24H3.3c-1.16 0-1.9-1.25-1.32-2.25l6.7-11.6ZM10 7a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 10 7Zm0 8a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z"
          />
        </svg>
      ) : null}
      <span>
        {percent} %{needsReview ? ' · prüfen' : ''}
      </span>
    </span>
  );
}
