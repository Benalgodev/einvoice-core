# NOTES — einvoice-core
- Python ≥ 3.10, aucune dépendance runtime ; dev : pytest + ruff (line-length 100). CI : GitHub Actions 3.10/3.12.
- Montants en `Decimal`, arrondi ROUND_HALF_UP au centime (`totals.r2`).
- TVA calculée par groupe (catégorie, taux) sur base arrondie, jamais ligne à ligne.
- `Invoice.declared` (DeclaredTotals) = totaux lus dans le fichier ; None = absent donc ignoré.
- `check_totals(inv, tolerance)` → liste de `Finding` (règle BR-CO-10..16, BT, déclaré, calculé).
- Piège : catégorie ≠ S impose taux 0 (ValueError dans compute_totals).
- Données de test fictives uniquement (tests/fixtures).
- `read_cii` : XPath BT→CII dans cii.py ; dates format 102 seul ; CII et UBL de test donnent le même `Invoice`.
- Suite : écriture UBL/CII depuis le modèle (round-trip avec les lecteurs).
