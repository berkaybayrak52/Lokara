"""Number formatting at the render boundary.

Engine values are scaled integers (money = cents, areas/weights = ×100
fixed-point). Everything in this module runs *after* the de-scaling and turns a
``Decimal`` into the string a human reads — German grouping, at most two
decimals, trailing zeros suppressed.

The largest-remainder helper is here for the same reason the engine has one: a
column of rounded figures printed under a rounded total has to add up **as
printed**. Rounding each value on its own prints ``20 + 5,95 + 3,02 + 3,02 + 8
= 39,99`` under a total of ``40``, and a document that is supposed to add up
then does not (docs/08 → "Display rounding of a fractional Bemessung").
"""

from collections.abc import Sequence
from decimal import ROUND_FLOOR, Decimal

# Two decimals is the display grid of every non-money figure on the statement.
DISPLAY_STEP = Decimal("0.01")


def format_number_de(value: Decimal) -> str:
    """German number formatting for non-money figures (weights, intensities)."""
    is_integral = value == value.to_integral_value()
    grouped = f"{int(value):,}" if is_integral else f"{value.normalize():,f}"
    return grouped.replace(",", "\0").replace(".", ",").replace("\0", ".")


def format_co2_intensity_de(value: Decimal) -> str:
    """German CO2 intensity with the engine's fixed one-decimal precision."""
    grouped = f"{value:,.1f}"
    return grouped.replace(",", "\0").replace(".", ",").replace("\0", ".")


def display_figure(value: Decimal) -> Decimal:
    """At most two decimals. ``format_number_de`` drops the trailing zeros."""
    return value.quantize(DISPLAY_STEP)


def largest_remainder_display(values: Sequence[Decimal], total: Decimal) -> list[Decimal]:
    """Round a column to two decimals so it sums to ``total`` exactly as printed.

    Same idiom the engines use for cents (docs/03 → Rounding): floor every value,
    then hand the missing hundredths to the largest remainders, ties broken by
    the stable order the values arrive in — which is the order the parties are
    printed in, so the result is reproducible from the page.
    """
    floors = [value.quantize(DISPLAY_STEP, rounding=ROUND_FLOOR) for value in values]
    shortfall = int((total - sum(floors, Decimal(0))) / DISPLAY_STEP)
    if shortfall <= 0:
        return floors
    remainders = [value - floor for value, floor in zip(values, floors, strict=True)]
    order = sorted(range(len(values)), key=lambda index: (-remainders[index], index))
    rounded = list(floors)
    for index in order[:shortfall]:
        rounded[index] += DISPLAY_STEP
    return rounded
