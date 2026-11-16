"""Modèle sémantique EN 16931 (sous-ensemble). Les identifiants BT/BG sont en commentaire."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class VatCategory(str, Enum):
    """UNTDID 5305 — catégories de TVA autorisées par l'EN 16931 (BT-118 / BT-151)."""
    STANDARD = "S"
    ZERO = "Z"
    EXEMPT = "E"
    REVERSE_CHARGE = "AE"
    INTRA_EU = "K"
    EXPORT = "G"
    OUT_OF_SCOPE = "O"

    @property
    def requires_exemption_reason(self) -> bool:
        # BR-E-10, BR-AE-10, BR-IC-10, BR-G-10, BR-O-10
        return self in {VatCategory.EXEMPT, VatCategory.REVERSE_CHARGE,
                        VatCategory.INTRA_EU, VatCategory.EXPORT, VatCategory.OUT_OF_SCOPE}

    @property
    def forces_zero_rate(self) -> bool:
        return self is not VatCategory.STANDARD


@dataclass
class Party:
    name: str                       # BT-27 / BT-44
    vat_id: str | None = None       # BT-31 / BT-48
    siren: str | None = None        # BT-30 / BT-47 (schéma 0002)
    country: str = "FR"             # BT-40 / BT-55


@dataclass
class AllowanceCharge:
    """BG-20 (remise document) / BG-21 (charge document)."""
    is_charge: bool
    amount: Decimal                 # BT-92 / BT-99
    vat_category: VatCategory       # BT-95 / BT-102
    vat_rate: Decimal               # BT-96 / BT-103
    reason: str | None = None       # BT-97 / BT-104


@dataclass
class InvoiceLine:
    """BG-25."""
    line_id: str                    # BT-126
    quantity: Decimal               # BT-129
    unit_price: Decimal             # BT-146 (prix net)
    vat_category: VatCategory       # BT-151
    vat_rate: Decimal               # BT-152
    name: str = ""                  # BT-153
    base_quantity: Decimal = Decimal(1)  # BT-149
    line_allowances: Decimal = Decimal(0)
    line_charges: Decimal = Decimal(0)

    @property
    def net_amount(self) -> Decimal:
        """BT-131 = qté × (prix / qté de base) − remises ligne + charges ligne."""
        return self.quantity * self.unit_price / self.base_quantity \
            - self.line_allowances + self.line_charges


@dataclass
class Invoice:
    number: str                     # BT-1
    issue_date: date                # BT-2
    type_code: str                  # BT-3 (380 facture, 381 avoir…)
    currency: str                   # BT-5
    seller: Party                   # BG-4
    buyer: Party                    # BG-7
    lines: list[InvoiceLine] = field(default_factory=list)
    allowances_charges: list[AllowanceCharge] = field(default_factory=list)
    exemption_reasons: dict[VatCategory, str] = field(default_factory=dict)  # BT-120/121
    prepaid_amount: Decimal = Decimal(0)     # BT-113
    rounding_amount: Decimal = Decimal(0)    # BT-114
