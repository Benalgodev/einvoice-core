"""Lecture d'une facture UBL 2.1 vers le modèle EN 16931 (sous-ensemble)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

from .model import AllowanceCharge, DeclaredTotals, Invoice, InvoiceLine, Party, VatCategory

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def _t(el: ET.Element, path: str, default: str | None = None) -> str | None:
    found = el.find(path, NS)
    return found.text.strip() if found is not None and found.text else default


def _d(el: ET.Element, path: str, default: str = "0") -> Decimal:
    return Decimal(_t(el, path, default))


def _opt(el: ET.Element, path: str) -> Decimal | None:
    txt = _t(el, path)
    return Decimal(txt) if txt is not None else None


def _party(el: ET.Element | None) -> Party:
    if el is None:
        return Party(name="")
    p = el.find("cac:Party", NS)
    return Party(
        name=_t(p, "cac:PartyLegalEntity/cbc:RegistrationName")
        or _t(p, "cac:PartyName/cbc:Name", ""),
        vat_id=_t(p, "cac:PartyTaxScheme/cbc:CompanyID"),
        siren=_t(p, "cac:PartyLegalEntity/cbc:CompanyID"),
        country=_t(p, "cac:PostalAddress/cac:Country/cbc:IdentificationCode", "FR"),
    )


def read_ubl(source: str | Path | bytes) -> Invoice:
    root = ET.fromstring(source) if isinstance(source, bytes) else ET.parse(source).getroot()
    lines = []
    for ln in root.findall("cac:InvoiceLine", NS):
        tax = ln.find("cac:Item/cac:ClassifiedTaxCategory", NS)
        lines.append(InvoiceLine(
            line_id=_t(ln, "cbc:ID", ""),
            quantity=_d(ln, "cbc:InvoicedQuantity"),
            unit_price=_d(ln, "cac:Price/cbc:PriceAmount"),
            base_quantity=_d(ln, "cac:Price/cbc:BaseQuantity", "1"),
            vat_category=VatCategory(_t(tax, "cbc:ID")),
            vat_rate=_d(tax, "cbc:Percent"),
            name=_t(ln, "cac:Item/cbc:Name", ""),
        ))
    acs = []
    for ac in root.findall("cac:AllowanceCharge", NS):
        tax = ac.find("cac:TaxCategory", NS)
        acs.append(AllowanceCharge(
            is_charge=_t(ac, "cbc:ChargeIndicator") == "true",
            amount=_d(ac, "cbc:Amount"),
            vat_category=VatCategory(_t(tax, "cbc:ID")),
            vat_rate=_d(tax, "cbc:Percent"),
            reason=_t(ac, "cbc:AllowanceChargeReason"),
        ))
    return Invoice(
        number=_t(root, "cbc:ID", ""),
        issue_date=date.fromisoformat(_t(root, "cbc:IssueDate")),
        type_code=_t(root, "cbc:InvoiceTypeCode", "380"),
        currency=_t(root, "cbc:DocumentCurrencyCode", "EUR"),
        seller=_party(root.find("cac:AccountingSupplierParty", NS)),
        buyer=_party(root.find("cac:AccountingCustomerParty", NS)),
        lines=lines,
        allowances_charges=acs,
        prepaid_amount=_d(root, "cac:LegalMonetaryTotal/cbc:PrepaidAmount"),
        rounding_amount=_d(root, "cac:LegalMonetaryTotal/cbc:PayableRoundingAmount"),
        declared=DeclaredTotals(
            line_total=_opt(root, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount"),
            allowance_total=_opt(root, "cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount"),
            charge_total=_opt(root, "cac:LegalMonetaryTotal/cbc:ChargeTotalAmount"),
            tax_exclusive=_opt(root, "cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount"),
            tax_total=_opt(root, "cac:TaxTotal/cbc:TaxAmount"),
            tax_inclusive=_opt(root, "cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount"),
            payable=_opt(root, "cac:LegalMonetaryTotal/cbc:PayableAmount"),
        ),
    )
