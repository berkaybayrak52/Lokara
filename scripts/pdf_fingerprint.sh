#!/usr/bin/env bash
# A hash of the statement PDF that ignores the two things that legitimately change.
#
# Why this exists. Slice 3 was specified as "not demo-visible by design" and the criterion
# I set for it — "the md5 must equal <captured value>" — could never have passed. Two
# renders of *identical* code differ by exactly four bytes: the seconds digits of
# /CreationDate and /ModDate. A baseline captured once and never re-derived is not a
# baseline, it is a number that happens to be written down.
#
# Normalizing the timestamps gives a fingerprint that answers the question actually being
# asked: did this change alter what a human reads? An engine refactor, a field added to a
# result shape, a rename — all should leave it untouched. A de-scaling regression, a
# reworded footer, a new disclosure row should not.
#
#   scripts/pdf_fingerprint.sh                       # the demo statement
#   scripts/pdf_fingerprint.sh path/to/other.pdf
#
# Typical use, around a slice that claims to change nothing visible:
#
#   git stash && scripts/pdf_fingerprint.sh > /tmp/before
#   git stash pop && uv run lokara-pdf-demo
#   diff <(scripts/pdf_fingerprint.sh) /tmp/before
#
# Deliberately NOT wired into gate.sh: most slices are supposed to change the document, so
# a standing assertion would be red by default and quickly ignored. This is a tool you
# reach for when a slice claims invisibility, and it makes that claim checkable instead of
# asserted.

set -uo pipefail
cd "$(dirname "$0")/.."

PDF="${1:-packages/pdf/output/nk-heating-statement-demo.pdf}"

if [[ ! -f "$PDF" ]]; then
  echo "pdf_fingerprint: $PDF does not exist — run 'uv run lokara-pdf-demo' first" >&2
  exit 2
fi

# macOS ships `md5`, GNU ships `md5sum`. Without this the pipeline printed an empty
# hash and still exited 0 — before and after would have compared equal, which is the
# exact failure this script exists to catch. A verification tool must never be able to
# pass by producing nothing.
if command -v md5sum >/dev/null 2>&1; then
  md5_of_stdin() { md5sum | cut -d' ' -f1; }
elif command -v md5 >/dev/null 2>&1; then
  md5_of_stdin() { md5 -q; }
else
  echo "pdf_fingerprint: neither md5sum nor md5 found" >&2
  exit 2
fi

# D:YYYYMMDDHHMMSS -> D:<normalized>. Everything else is compared byte for byte.
hash=$(LC_ALL=C sed -E 's/D:[0-9]{14}/D:00000000000000/g' "$PDF" | md5_of_stdin)
if [[ -z "$hash" ]]; then
  echo "pdf_fingerprint: produced an empty hash — refusing to report success" >&2
  exit 2
fi
size=$(wc -c < "$PDF" | tr -d ' ')

printf '%s  %s bytes  %s\n' "$hash" "$size" "$PDF"
