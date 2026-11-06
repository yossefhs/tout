#!/home/user/.venv-webtest/bin/python
"""quota.py — dit à la session planifiée si elle peut encore produire un e-mail maintenant, et combien.

Usage :
  quota.py [--config config.json] [--data-dir data] [--maintenant 2026-11-05T10:30]

Lit config.json (mode, plafond_quotidien, plafond_horaire, heures_envoi) et data/ledger.csv, puis affiche un JSON :
  mode, dans_fenetre (jour ouvré et heure dans heures_envoi, fuseau Europe/Paris), prochaine_fenetre,
  aujourd_hui {sent, drafted, total_comptes}, derniere_heure (sent+drafted datés d'aujourd'hui : le ledger n'a que
  la date, donc le compteur horaire est estimé à partir des notes « heure=HH:MM » posées par la session),
  restant_jour, restant_heure, peut_produire (booléen), motif.
En mode review, les brouillons comptent dans le plafond (c'est ce que Guillaume aura à relire).
En mode auto, seuls les envois comptent, et la fenêtre horaire est bloquante.
Aucune écriture. Codes : 0 ok ; 2 fichiers invalides.
"""
import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
CONFIG_DEFAUT = os.path.join(PIPELINE, "config.json")
DATA_DEFAUT = os.path.join(PIPELINE, "data")
HEURES_DEFAUT = {"debut": "09:00", "fin": "18:00", "jours": [0, 1, 2, 3, 4], "fuseau": "Europe/Paris"}


def lire_csv(chemin):
    if not os.path.isfile(chemin) or os.path.getsize(chemin) == 0:
        return []
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def parse_hm(s, defaut):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", (s or "").strip())
    if not m:
        return defaut
    h, mi = int(m.group(1)), int(m.group(2))
    return (h, mi) if 0 <= h <= 23 and 0 <= mi <= 59 else defaut


def prochaine_fenetre(maintenant, debut, jours):
    for d in range(0, 8):
        jour = (maintenant + timedelta(days=d)).replace(hour=debut[0], minute=debut[1], second=0, microsecond=0)
        if jour.weekday() in jours and jour > maintenant:
            return jour
    return None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=CONFIG_DEFAUT)
    p.add_argument("--data-dir", default=DATA_DEFAUT)
    p.add_argument("--maintenant", help="date-heure ISO locale (tests) ; défaut : maintenant, Europe/Paris")
    a = p.parse_args(argv)

    try:
        with open(a.config, encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("config.json doit contenir un objet")
        ledger = lire_csv(os.path.join(a.data_dir, "ledger.csv"))
    except (OSError, ValueError, json.JSONDecodeError, csv.Error) as e:
        print(json.dumps({"ok": False, "erreur": f"{type(e).__name__} : {e}"}, ensure_ascii=False))
        return 2

    mode = cfg.get("mode") if cfg.get("mode") in ("review", "auto") else "review"
    plafond_jour = int(cfg.get("plafond_quotidien") or 10)
    plafond_heure = int(cfg.get("plafond_horaire") or max(1, plafond_jour))
    h = dict(HEURES_DEFAUT)
    h.update({k: v for k, v in (cfg.get("heures_envoi") or {}).items() if v not in (None, "")})
    tz = ZoneInfo(h.get("fuseau") or "Europe/Paris") if ZoneInfo else None
    if a.maintenant:
        maintenant = datetime.fromisoformat(a.maintenant)
        if tz and maintenant.tzinfo is None:
            maintenant = maintenant.replace(tzinfo=tz)
    else:
        maintenant = datetime.now(tz) if tz else datetime.now()
    debut, fin = parse_hm(h.get("debut"), (9, 0)), parse_hm(h.get("fin"), (18, 0))
    jours = [int(j) for j in (h.get("jours") or [0, 1, 2, 3, 4]) if str(j).isdigit() and 0 <= int(j) <= 6]
    hm = (maintenant.hour, maintenant.minute)
    dans_fenetre = maintenant.weekday() in jours and debut <= hm <= fin

    aujourd_hui = maintenant.strftime("%Y-%m-%d")
    du_jour = [r for r in ledger if (r.get("date") or "").startswith(aujourd_hui)]
    sent = [r for r in du_jour if r.get("statut") == "sent"]
    drafted = [r for r in du_jour if r.get("statut") == "drafted"]
    comptes = sent + (drafted if mode == "review" else [])
    # compteur horaire : notes « heure=HH:MM » (posées par la session) ; sans note, la ligne compte comme récente (prudence)
    heure_limite = maintenant - timedelta(hours=1)
    recents = 0
    for r in comptes:
        m = re.search(r"heure=(\d{1,2}):(\d{2})", r.get("notes") or "")
        if not m:
            recents += 1
            continue
        t = maintenant.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if t >= heure_limite:
            recents += 1

    restant_jour = max(0, plafond_jour - len(comptes))
    restant_heure = max(0, plafond_heure - recents)
    motif = ""
    if restant_jour == 0:
        motif = f"plafond quotidien atteint ({plafond_jour})"
    elif restant_heure == 0:
        motif = f"plafond horaire atteint ({plafond_heure}) : reprendre plus tard dans la session ou à la prochaine exécution"
    elif not dans_fenetre and mode == "auto":
        motif = "hors fenêtre d'envoi (mode auto : aucun envoi)"
    peut = restant_jour > 0 and restant_heure > 0 and (dans_fenetre or mode == "review")
    if peut and not dans_fenetre:
        motif = "hors fenêtre d'envoi : des brouillons peuvent être préparés (mode review), rien n'est envoyé"
    prochaine = prochaine_fenetre(maintenant, debut, jours)
    print(json.dumps({
        "ok": True, "mode": mode, "maintenant": maintenant.isoformat(timespec="minutes"),
        "fenetre": {"debut": f"{debut[0]:02d}:{debut[1]:02d}", "fin": f"{fin[0]:02d}:{fin[1]:02d}", "jours": jours,
                    "fuseau": h.get("fuseau") or "Europe/Paris"},
        "dans_fenetre": dans_fenetre,
        "prochaine_fenetre": prochaine.isoformat(timespec="minutes") if prochaine else None,
        "plafonds": {"quotidien": plafond_jour, "horaire": plafond_heure},
        "aujourd_hui": {"sent": len(sent), "drafted": len(drafted), "comptes": len(comptes), "derniere_heure": recents},
        "restant_jour": restant_jour, "restant_heure": restant_heure,
        "peut_produire": peut, "motif": motif,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
