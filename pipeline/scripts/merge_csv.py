#!/usr/bin/env python3
"""Fusionne plusieurs CSV de leads (séparateur ;) en un seul, dédoublonné par SIREN.

  merge_csv.py <sortie.csv> <entree1.csv> [entree2.csv ...]

- Union des colonnes (ordre de première apparition), BOM UTF-8 conservé en sortie (lecture Excel).
- Les fichiers absents ou vides sont ignorés (signalés sur stderr).
- Résumé JSON sur stdout : {"sortie", "fichiers_lus", "lignes_lues", "lignes_uniques"}.
"""
import csv
import json
import os
import sys

csv.field_size_limit(10_000_000)


def lire(chemin):
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f, delimiter=";")
        return r.fieldnames or [], list(r)


def main(argv):
    if len(argv) < 3 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(argv) >= 2 and argv[1] in ("-h", "--help") else 1
    sortie, entrees = argv[1], argv[2:]
    colonnes, lignes, vus = [], [], set()
    lus, total = 0, 0
    for ch in entrees:
        if not os.path.exists(ch) or os.path.getsize(ch) == 0:
            print(f"  (ignoré : {ch} absent ou vide)", file=sys.stderr)
            continue
        try:
            cols, rows = lire(ch)
        except Exception as e:  # fichier corrompu : on continue avec les autres
            print(f"  (ignoré : {ch} illisible : {e})", file=sys.stderr)
            continue
        lus += 1
        for c in cols:
            if c not in colonnes:
                colonnes.append(c)
        for row in rows:
            total += 1
            siren = (row.get("siren") or "").strip()
            cle = siren or json.dumps(row, sort_keys=True)
            if cle in vus:
                continue
            vus.add(cle)
            lignes.append(row)
    os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
    with open(sortie, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, delimiter=";", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for row in lignes:
            w.writerow({c: row.get(c, "") for c in colonnes})
    print(json.dumps({"sortie": sortie, "fichiers_lus": lus, "lignes_lues": total, "lignes_uniques": len(lignes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
