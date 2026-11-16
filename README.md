# einvoice-core

[![CI](https://github.com/Benalgodev/einvoice-core/actions/workflows/ci.yml/badge.svg)](https://github.com/Benalgodev/einvoice-core/actions)

Noyau Python pour la facturation électronique européenne : modèle sémantique **EN 16931**, chaîne de calcul des totaux, ventilation TVA, lecture **UBL 2.1** (CII et Factur-X en cours).

## Pourquoi

En intégration ERP → plateforme agréée, la majorité des rejets ne viennent pas du format mais du **calcul** : TVA arrondie ligne à ligne au lieu de par taux, remise document mal ventilée, catégorie `AE` envoyée avec un taux à 20 %. Cette bibliothèque applique les règles de la norme (BR-CO-10 à BR-CO-16, BR-*-08) pour recalculer une facture et repérer l'écart avant qu'il parte.

## Exemple

```python
from einvoice_core import read_ubl, compute_totals

t = compute_totals(read_ubl("facture.xml"))
print(t.tax_exclusive, t.tax_total, t.payable)
for b in t.breakdown:
    print(b.category.value, b.rate, b.taxable_amount, b.tax_amount)
```

## Ce qui est couvert

- Modèle : BG-4/BG-7 (parties), BG-20/21 (remises et charges document), BG-25 (lignes), BG-22/23 (totaux et ventilation)
- Catégories TVA UNTDID 5305 : S, Z, E, AE, K, G, O
- Calcul TVA par couple (catégorie, taux), arrondi `ROUND_HALF_UP` au centime

Feuille de route : [ROADMAP.md](ROADMAP.md). Toutes les factures d'exemple sont fictives.

## Installation

```bash
pip install -e ".[dev]" && pytest
```
