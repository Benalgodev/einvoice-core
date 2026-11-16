"""Chaîne de calcul des totaux EN 16931 (BG-22) et ventilation TVA (BG-23)."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .model import Invoice, VatCategory

CENT = Decimal("0.01")


def r2(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class VatBreakdown:
    category: VatCategory           # BT-118
    rate: Decimal                   # BT-119
    taxable_amount: Decimal         # BT-116
    tax_amount: Decimal             # BT-117


@dataclass(frozen=True)
class DocumentTotals:
    line_total: Decimal             # BT-106
    allowance_total: Decimal        # BT-107
    charge_total: Decimal           # BT-108
    tax_exclusive: Decimal          # BT-109
    tax_total: Decimal              # BT-110
    tax_inclusive: Decimal          # BT-112
    prepaid: Decimal                # BT-113
    rounding: Decimal               # BT-114
    payable: Decimal                # BT-115
    breakdown: tuple[VatBreakdown, ...]


def compute_totals(inv: Invoice) -> DocumentTotals:
    """Calcule BG-22/BG-23 selon BR-CO-10 à BR-CO-16 et BR-S-08 / BR-*-08.

    La TVA est calculée par groupe (catégorie, taux) sur la base arrondie, puis
    arrondie — et non ligne par ligne — ce qui évite les écarts de centimes
    classiques des exports ERP.
    """
    bases: dict[tuple[VatCategory, Decimal], Decimal] = defaultdict(Decimal)
    line_total = Decimal(0)
    for line in inv.lines:
        net = r2(line.net_amount)
        line_total += net
        bases[(line.vat_category, line.vat_rate)] += net

    allowance_total = charge_total = Decimal(0)
    for ac in inv.allowances_charges:
        amt = r2(ac.amount)
        if ac.is_charge:
            charge_total += amt
            bases[(ac.vat_category, ac.vat_rate)] += amt
        else:
            allowance_total += amt
            bases[(ac.vat_category, ac.vat_rate)] -= amt

    breakdown = []
    for (cat, rate), base in sorted(bases.items(), key=lambda kv: (kv[0][0].value, kv[0][1])):
        if cat.forces_zero_rate and rate != 0:
            raise ValueError(f"Catégorie {cat.value} avec taux {rate} : le taux doit être 0")
        tax = r2(base * rate / 100) if cat is VatCategory.STANDARD else Decimal("0.00")
        breakdown.append(VatBreakdown(cat, rate, r2(base), tax))

    tax_exclusive = line_total - allowance_total + charge_total          # BR-CO-13
    tax_total = sum((b.tax_amount for b in breakdown), Decimal(0))    # BR-CO-14
    tax_inclusive = tax_exclusive + tax_total                            # BR-CO-15
    payable = tax_inclusive - inv.prepaid_amount + inv.rounding_amount   # BR-CO-16
    return DocumentTotals(r2(line_total), r2(allowance_total), r2(charge_total),
                          r2(tax_exclusive), r2(tax_total), r2(tax_inclusive),
                          r2(inv.prepaid_amount), r2(inv.rounding_amount), r2(payable),
                          tuple(breakdown))
