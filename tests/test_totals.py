from decimal import Decimal as D
from pathlib import Path

import pytest

from einvoice_core import VatCategory, compute_totals, read_ubl
from einvoice_core.model import Invoice, InvoiceLine, Party

FIX = Path(__file__).parent / "fixtures"


def test_ubl_round_trip_totals():
    inv = read_ubl(FIX / "facture_fictive.xml")
    t = compute_totals(inv)
    assert t.line_total == D("283.47")          # 3 × 74.99 + 58.50
    assert t.tax_exclusive == D("273.47")       # − remise 10.00
    by_rate = {b.rate: b for b in t.breakdown}
    assert by_rate[D(20)].taxable_amount == D("214.97")
    assert by_rate[D(20)].tax_amount == D("42.99")
    assert by_rate[D("5.5")].tax_amount == D("3.22")
    assert t.payable == D("319.68")


def test_vat_computed_per_group_not_per_line():
    # 3 lignes à 0,35 € HT : TVA ligne à ligne = 3 × 0,07 = 0,21 ; par groupe = 0,21 (1,05 × 20 %)
    # 3 lignes à 0,33 € : ligne à ligne 3 × 0,07 = 0,21 ; par groupe 0,99 × 20 % = 0,20
    inv = Invoice("T", None, "380", "EUR", Party("a"), Party("b"), lines=[
        InvoiceLine(str(i), D(1), D("0.33"), VatCategory.STANDARD, D(20)) for i in range(3)
    ])
    assert compute_totals(inv).tax_total == D("0.20")


def test_reverse_charge_must_have_zero_rate():
    inv = Invoice("T", None, "380", "EUR", Party("a"), Party("b"), lines=[
        InvoiceLine("1", D(1), D(100), VatCategory.REVERSE_CHARGE, D(20))
    ])
    with pytest.raises(ValueError):
        compute_totals(inv)
