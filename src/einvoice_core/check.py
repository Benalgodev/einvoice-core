"""Contrôle des écarts entre totaux déclarés (BG-22) et totaux recalculés."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .model import Invoice
from .totals import compute_totals

# (champ, BT, règle EN 16931, libellé)
_RULES = (
    ("line_total", "BT-106", "BR-CO-10", "Somme des montants nets de lignes"),
    ("allowance_total", "BT-107", "BR-CO-11", "Somme des remises document"),
    ("charge_total", "BT-108", "BR-CO-12", "Somme des charges document"),
    ("tax_exclusive", "BT-109", "BR-CO-13", "Total HT"),
    ("tax_total", "BT-110", "BR-CO-14", "Total TVA"),
    ("tax_inclusive", "BT-112", "BR-CO-15", "Total TTC"),
    ("payable", "BT-115", "BR-CO-16", "Montant à payer"),
)


@dataclass(frozen=True)
class Finding:
    """Un écart détecté : règle violée, terme concerné, valeurs déclarée et calculée."""
    rule: str
    bt: str
    message: str
    declared: Decimal
    computed: Decimal

    def __str__(self) -> str:
        return f"[{self.rule}] {self.bt} {self.message} : déclaré {self.declared}, calculé {self.computed}"


def check_totals(inv: Invoice, tolerance: Decimal = Decimal("0.00")) -> list[Finding]:
    """Compare les totaux déclarés aux totaux recalculés ; un Finding par écart.

    Les totaux absents du document (None) sont ignorés. ``tolerance`` est l'écart
    absolu admis (0 par défaut : l'EN 16931 exige l'égalité au centime).
    """
    computed = compute_totals(inv)
    findings = []
    for attr, bt, rule, label in _RULES:
        declared = getattr(inv.declared, attr)
        if declared is None:
            continue
        expected = getattr(computed, attr)
        if abs(declared - expected) > tolerance:
            findings.append(Finding(rule, bt, f"{label} incohérent", declared, expected))
    return findings
