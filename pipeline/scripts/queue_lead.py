#!/home/user/.venv-webtest/bin/python
"""queue_lead.py — lit data/queue.csv et en extrait un lead en JSON (format attendu par build_email.py --lead).

Usage :
  queue_lead.py list  [--queue data/queue.csv] [--max N]          liste les leads (siren, nom, domaine, email, score)
  queue_lead.py get   --siren S | --domaine D | --index N          écrit le lead en JSON (stdout, ou --out lead.json)
  queue_lead.py count [--queue ...]                                 {"lignes": N}

Le CSV est celui de filter_queue.py (séparateur « ; », UTF-8 avec ou sans BOM), colonnes :
siren;nom;enseigne;naf;libelle_naf;adresse;cp;ville;dept;dirigeants;site;site_confiance;email;email_type;tel;score_lead;date_collecte
Aucune écriture dans queue.csv. Codes : 0 ok ; 1 lead introuvable ; 2 arguments ou fichier invalides.
"""
import argparse
import csv
import json
import os
import re
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
QUEUE_DEFAUT = os.path.join(PIPELINE, "data", "queue.csv")
COLONNES = ["siren", "nom", "enseigne", "naf", "libelle_naf", "adresse", "cp", "ville", "dept", "dirigeants", "site",
            "site_confiance", "email", "email_type", "tel", "score_lead", "date_collecte"]


def domaine_de(url):
    m = re.match(r"^(?:https?://)?([^/:?#\s]+)", (url or "").strip(), re.I)
    return m.group(1).lower().removeprefix("www.") if m else ""


def lire(chemin):
    if not os.path.isfile(chemin):
        raise FileNotFoundError(f"file introuvable : {chemin}")
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    res = []
    for r in lignes:
        if not r or not (r.get("siren") or r.get("site") or r.get("email")):
            continue
        lead = {k: (r.get(k) or "").strip() for k in COLONNES}
        try:
            lead["score_lead"] = int(float(lead["score_lead"])) if lead["score_lead"] else 0
        except ValueError:
            lead["score_lead"] = 0
        lead["domaine"] = domaine_de(lead["site"])
        res.append(lead)
    return res


def ecrire_atomique(chemin, contenu):
    dossier = os.path.dirname(os.path.abspath(chemin)) or "."
    os.makedirs(dossier, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".lead-", suffix=".tmp", dir=dossier)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenu)
        os.replace(tmp, chemin)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--queue", default=QUEUE_DEFAUT)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("list"); s.add_argument("--max", type=int, default=50)
    s = sp.add_parser("get"); s.add_argument("--siren"); s.add_argument("--domaine"); s.add_argument("--index", type=int)
    s.add_argument("--out", help="chemin de lead.json (sinon stdout)")
    sp.add_parser("count")
    a = p.parse_args(argv)

    try:
        leads = lire(a.queue)
    except (OSError, csv.Error, UnicodeDecodeError) as e:
        print(json.dumps({"ok": False, "erreur": f"{type(e).__name__} : {e}"}, ensure_ascii=False))
        return 2

    if a.cmd == "count":
        print(json.dumps({"ok": True, "lignes": len(leads), "queue": os.path.abspath(a.queue)}, ensure_ascii=False))
        return 0
    if a.cmd == "list":
        apercu = [{"index": i, "siren": l["siren"], "nom": l["enseigne"] or l["nom"], "domaine": l["domaine"],
                   "email": l["email"], "ville": l["ville"], "naf": l["naf"], "score_lead": l["score_lead"]}
                  for i, l in enumerate(leads[:max(0, a.max)])]
        print(json.dumps({"ok": True, "total": len(leads), "leads": apercu}, ensure_ascii=False))
        return 0

    if a.siren is None and a.domaine is None and a.index is None:
        print(json.dumps({"ok": False, "erreur": "--siren, --domaine ou --index requis"}, ensure_ascii=False))
        return 2
    lead = None
    if a.index is not None:
        lead = leads[a.index] if 0 <= a.index < len(leads) else None
    elif a.siren:
        si = re.sub(r"\D", "", a.siren)
        lead = next((l for l in leads if l["siren"] == si), None)
    else:
        d = domaine_de(a.domaine)
        lead = next((l for l in leads if l["domaine"] == d), None)
    if not lead:
        print(json.dumps({"ok": False, "erreur": "lead introuvable dans la file"}, ensure_ascii=False))
        return 1
    texte = json.dumps(lead, ensure_ascii=False, indent=2) + "\n"
    if a.out:
        ecrire_atomique(a.out, texte)
        print(json.dumps({"ok": True, "out": os.path.abspath(a.out), "siren": lead["siren"], "domaine": lead["domaine"],
                          "email": lead["email"]}, ensure_ascii=False))
    else:
        sys.stdout.write(texte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
