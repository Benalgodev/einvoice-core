from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path

import pytest

from einvoice_core import check_totals, compute_totals, read_cii, read_ubl

FIX = Path(__file__).parent / "fixtures"


def test_cii_reads_header_and_parties():
    inv = read_cii(FIX / "facture_fictive_cii.xml")
    assert (inv.number, inv.type_code, inv.currency) == ("FA-2026-0042", "380", "EUR")
    assert inv.issue_date.isoformat() == "2026-11-02"
    assert inv.seller.vat_id == "FR00123456789" and inv.seller.siren == "123456789"
    assert inv.buyer.name == "Client Exemple SARL"
    assert len(inv.lines) == 2 and len(inv.allowances_charges) == 1


def test_cii_equals_ubl_semantically():
    cii, ubl = read_cii(FIX / "facture_fictive_cii.xml"), read_ubl(FIX / "facture_fictive.xml")
    assert cii == ubl
    assert compute_totals(cii).payable == D("319.68")


def test_cii_consistent_and_mismatch_detected():
    inv = read_cii(FIX / "facture_fictive_cii.xml")
    assert check_totals(inv) == []
    inv.declared = replace(inv.declared, payable=D("320.00"))
    assert [f.rule for f in check_totals(inv)] == ["BR-CO-16"]


def test_cii_rejects_wrong_root_and_bad_date_format():
    with pytest.raises(ValueError, match="racine"):
        read_cii(b"<Invoice/>")
    xml = (FIX / "facture_fictive_cii.xml").read_bytes().replace(b'format="102"', b'format="610"')
    with pytest.raises(ValueError, match="format de date"):
        read_cii(xml)
