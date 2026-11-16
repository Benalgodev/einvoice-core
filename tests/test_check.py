from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path

from einvoice_core import check_totals, read_ubl

FIX = Path(__file__).parent / "fixtures" / "facture_fictive.xml"


def test_fixture_is_consistent():
    assert check_totals(read_ubl(FIX)) == []


def test_declared_payable_mismatch_reports_br_co_16():
    inv = read_ubl(FIX)
    inv.declared = replace(inv.declared, payable=D("319.70"), tax_total=D("46.00"))
    rules = {f.rule: f for f in check_totals(inv)}
    assert set(rules) == {"BR-CO-16", "BR-CO-14"}
    assert rules["BR-CO-16"].computed == D("319.68")
    assert "BT-115" in str(rules["BR-CO-16"])


def test_tolerance_and_absent_totals():
    inv = read_ubl(FIX)
    inv.declared = replace(inv.declared, payable=D("319.69"))
    assert len(check_totals(inv)) == 1
    assert check_totals(inv, tolerance=D("0.01")) == []
