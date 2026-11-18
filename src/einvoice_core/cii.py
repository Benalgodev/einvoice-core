"""Lecture d'une facture CII (UN/CEFACT CrossIndustryInvoice D16B) vers le modèle EN 16931.

Couvre les syntaxes EN 16931, Factur-X (profils EN 16931/Extended) et ZUGFeRD.
Le mapping suit le tableau de correspondance BT → XPath CII de la norme.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal
from pathlib import Path

from .model import AllowanceCharge, DeclaredTotals, Invoice, InvoiceLine, Party, VatCategory

NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
_TX = "rsm:SupplyChainTradeTransaction"
_AGR = f"{_TX}/ram:ApplicableHeaderTradeAgreement"
_SET = f"{_TX}/ram:ApplicableHeaderTradeSettlement"
_SUM = f"{_SET}/ram:SpecifiedTradeSettlementHeaderMonetarySummation"


def _t(el: ET.Element | None, path: str, default: str | None = None) -> str | None:
    found = el.find(path, NS) if el is not None else None
    return found.text.strip() if found is not None and found.text else default


def _d(el: ET.Element | None, path: str, default: str = "0") -> Decimal:
    return Decimal(_t(el, path, default))


def _opt(el: ET.Element | None, path: str) -> Decimal | None:
    txt = _t(el, path)
    return Decimal(txt) if txt is not None else None


def _parse_date(el: ET.Element, path: str) -> date:
    """BT-2 : udt:DateTimeString, format 102 (AAAAMMJJ) ou 610 (AAAAMM)."""
    node = el.find(path, NS)
    if node is None or not (node.text or "").strip():
        raise ValueError(f"date absente : {path}")
    txt = node.text.strip()
    fmt = node.get("format", "102")
    if fmt == "102":
        return date(int(txt[:4]), int(txt[4:6]), int(txt[6:8]))
    raise ValueError(f"format de date CII non géré : {fmt} (attendu 102)")


def _party(el: ET.Element | None) -> Party:
    if el is None:
        return Party(name="")
    vat = None
    for reg in el.findall("ram:SpecifiedTaxRegistration/ram:ID", NS):
        if reg.get("schemeID") == "VA" and reg.text:        # BT-31 / BT-48
            vat = reg.text.strip()
    return Party(
        name=_t(el, "ram:Name", ""),                                   # BT-27 / BT-44
        vat_id=vat,
        siren=_t(el, "ram:SpecifiedLegalOrganization/ram:ID"),         # BT-30 / BT-47
        country=_t(el, "ram:PostalTradeAddress/ram:CountryID", "FR"),  # BT-40 / BT-55
    )


def read_cii(source: str | Path | bytes) -> Invoice:
    """Lit un XML CII et retourne l'`Invoice` correspondant (totaux déclarés inclus)."""
    root = ET.fromstring(source) if isinstance(source, bytes) else ET.parse(source).getroot()
    if root.tag != f"{{{NS['rsm']}}}CrossIndustryInvoice":
        raise ValueError(f"racine inattendue : {root.tag} (attendu rsm:CrossIndustryInvoice)")
    lines = []
    for ln in root.findall(f"{_TX}/ram:IncludedSupplyChainTradeLineItem", NS):
        tax = ln.find("ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax", NS)
        price = "ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice"
        lines.append(InvoiceLine(
            line_id=_t(ln, "ram:AssociatedDocumentLineDocument/ram:LineID", ""),  # BT-126
            quantity=_d(ln, "ram:SpecifiedLineTradeDelivery/ram:BilledQuantity"),  # BT-129
            unit_price=_d(ln, f"{price}/ram:ChargeAmount"),                        # BT-146
            base_quantity=_d(ln, f"{price}/ram:BasisQuantity", "1"),               # BT-149
            vat_category=VatCategory(_t(tax, "ram:CategoryCode")),                 # BT-151
            vat_rate=_d(tax, "ram:RateApplicablePercent"),                         # BT-152
            name=_t(ln, "ram:SpecifiedTradeProduct/ram:Name", ""),                 # BT-153
        ))
    acs = []
    for ac in root.findall(f"{_SET}/ram:SpecifiedTradeAllowanceCharge", NS):
        acs.append(AllowanceCharge(
            is_charge=_t(ac, "ram:ChargeIndicator/udt:Indicator") == "true",
            amount=_d(ac, "ram:ActualAmount"),                       # BT-92 / BT-99
            vat_category=VatCategory(_t(ac, "ram:CategoryTradeTax/ram:CategoryCode")),
            vat_rate=_d(ac, "ram:CategoryTradeTax/ram:RateApplicablePercent"),
            reason=_t(ac, "ram:Reason"),                             # BT-97 / BT-104
        ))
    summ = root.find(_SUM, NS)
    return Invoice(
        number=_t(root, "rsm:ExchangedDocument/ram:ID", ""),                       # BT-1
        issue_date=_parse_date(
            root, "rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString"),   # BT-2
        type_code=_t(root, "rsm:ExchangedDocument/ram:TypeCode", "380"),           # BT-3
        currency=_t(root, f"{_SET}/ram:InvoiceCurrencyCode", "EUR"),               # BT-5
        seller=_party(root.find(f"{_AGR}/ram:SellerTradeParty", NS)),
        buyer=_party(root.find(f"{_AGR}/ram:BuyerTradeParty", NS)),
        lines=lines,
        allowances_charges=acs,
        prepaid_amount=_d(summ, "ram:TotalPrepaidAmount"),                         # BT-113
        rounding_amount=_d(summ, "ram:RoundingAmount"),                            # BT-114
        declared=DeclaredTotals(
            line_total=_opt(summ, "ram:LineTotalAmount"),            # BT-106
            allowance_total=_opt(summ, "ram:AllowanceTotalAmount"),  # BT-107
            charge_total=_opt(summ, "ram:ChargeTotalAmount"),        # BT-108
            tax_exclusive=_opt(summ, "ram:TaxBasisTotalAmount"),     # BT-109
            tax_total=_opt(summ, "ram:TaxTotalAmount"),              # BT-110
            tax_inclusive=_opt(summ, "ram:GrandTotalAmount"),        # BT-112
            payable=_opt(summ, "ram:DuePayableAmount"),              # BT-115
        ),
    )
