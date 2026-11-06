#!/home/user/.venv-webtest/bin/python
"""ledger.py — registre de prospection (data/ledger.csv) et liste d'opposition (data/opposition.csv).

Usage :
  ledger.py add   --siren S --domaine D --email E --statut queued [--notes ...]
  ledger.py set   --domaine D [--statut S] [--thread_id T] [--draft_id I] [--maquette_url U] [--notes N] [--email E]
  ledger.py check --email E | --domaine D
  ledger.py stop  --valeur V --source SRC [--type email|domaine|siren|bounce]   (bounce : opposition d'une adresse en erreur, statut bounced)
  ledger.py list  [--statut S]
  options communes : --data-dir <dossier> (défaut : <pipeline>/data)

Schémas (séparateur « ; », UTF-8) :
  ledger.csv     : date;siren;domaine;email;statut;thread_id;draft_id;maquette_url;notes
  opposition.csv : valeur;type;date;source
Statuts : queued, audited, skipped, drafted, sent, replied, interested, stop, bounced, won, lost.

Les fichiers ne sont créés que s'ils n'existent pas (O_EXCL) ; toute réécriture passe par un fichier
temporaire puis os.replace ; un verrou (flock sur data/.ledger.lock) sérialise les écritures avec les autres
composants. Sortie JSON sur stdout. Codes : 0 ok ; 1 non trouvé / refusé ; 2 arguments invalides.
"""
import argparse
import csv
import fcntl
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import date

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
DATA_DEFAUT = os.path.join(PIPELINE, "data")
ENTETE_LEDGER = ["date", "siren", "domaine", "email", "statut", "thread_id", "draft_id", "maquette_url", "notes"]
ENTETE_OPPOSITION = ["valeur", "type", "date", "source"]
STATUTS = ["queued", "audited", "skipped", "drafted", "sent", "replied", "interested", "stop", "bounced", "won", "lost"]
WEBMAILS = {"gmail.com", "googlemail.com", "hotmail.fr", "hotmail.com", "outlook.fr", "outlook.com", "live.fr", "live.com",
            "yahoo.fr", "yahoo.com", "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr", "neuf.fr", "laposte.net", "bbox.fr",
            "icloud.com", "aol.com", "gmx.fr", "gmx.com", "protonmail.com", "proton.me", "nordnet.fr", "numericable.fr"}


# ----------------------------------------------------------------------------
# Fichiers
# ----------------------------------------------------------------------------
@contextmanager
def verrou(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    fd = os.open(os.path.join(data_dir, ".ledger.lock"), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def creer_si_absent(chemin, entete):
    """Crée le fichier avec son en-tête seulement s'il n'existe pas (jamais d'écrasement)."""
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    try:
        fd = os.open(chemin, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        if os.path.getsize(chemin) == 0:  # fichier vide laissé par un autre composant : on pose l'en-tête
            with open(chemin, "w", encoding="utf-8", newline="") as f:
                csv.writer(f, delimiter=";", lineterminator="\n").writerow(entete)
            return True
        return False
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";", lineterminator="\n").writerow(entete)
    return True


def lire(chemin, entete):
    if not os.path.exists(chemin) or os.path.getsize(chemin) == 0:
        return []
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        lignes = list(csv.DictReader(f, delimiter=";"))
    return [{k: (r.get(k) or "").strip() for k in entete} for r in lignes]


def ecrire_tout(chemin, entete, lignes):
    dossier = os.path.dirname(os.path.abspath(chemin))
    fd, tmp = tempfile.mkstemp(prefix=".ledger-", suffix=".tmp", dir=dossier)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=entete, delimiter=";", lineterminator="\n", extrasaction="ignore")
            w.writeheader()
            for r in lignes:
                w.writerow({k: nettoyer(r.get(k, "")) for k in entete})
        os.replace(tmp, chemin)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def ajouter_ligne(chemin, entete, ligne):
    creer_si_absent(chemin, entete)
    with open(chemin, "a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=entete, delimiter=";", lineterminator="\n", extrasaction="ignore").writerow(
            {k: nettoyer(ligne.get(k, "")) for k in entete})


def nettoyer(v):
    return re.sub(r"[\r\n]+", " ", str(v or "")).strip()


# ----------------------------------------------------------------------------
# Normalisation
# ----------------------------------------------------------------------------
def norm_domaine(v):
    if not v:
        return ""
    m = re.match(r"^(?:https?://)?([^/:?#\s]+)", str(v).strip(), re.I)
    return (m.group(1).lower().removeprefix("www.") if m else str(v).strip().lower())


def norm_email(v):
    return (v or "").strip().lower()


def norm_siren(v):
    return re.sub(r"\D", "", v or "")


def type_valeur(v, force=None):
    if force:
        return force
    if "@" in v:
        return "email"
    if v.isdigit() and len(v) == 9:
        return "siren"
    return "domaine"


# ----------------------------------------------------------------------------
# Commandes
# ----------------------------------------------------------------------------
def cmd_add(a, data_dir):
    if a.statut not in STATUTS:
        return 2, {"ok": False, "erreur": f"statut inconnu « {a.statut} » (attendu : {', '.join(STATUTS)})"}
    dom, em, si = norm_domaine(a.domaine), norm_email(a.email), norm_siren(a.siren)
    if not (dom or em or si):
        return 2, {"ok": False, "erreur": "au moins un identifiant requis : --siren, --domaine ou --email"}
    chemin = os.path.join(data_dir, "ledger.csv")
    with verrou(data_dir):
        bloque = _opposition_match(data_dir, dom, em, si)
        if bloque and a.statut != "stop":
            return 1, {"ok": False, "erreur": "valeur présente dans opposition.csv : ajout refusé", "opposition": bloque}
        existants = [r for r in lire(chemin, ENTETE_LEDGER) if (dom and r["domaine"] == dom) or (em and r["email"] == em)]
        if existants and not a.force:
            return 1, {"ok": False, "erreur": "déjà présent dans le registre (utiliser set, ou --force pour une 2e ligne)",
                       "lignes": existants}
        ligne = {"date": date.today().isoformat(), "siren": si, "domaine": dom, "email": em, "statut": a.statut,
                 "thread_id": a.thread_id or "", "draft_id": a.draft_id or "", "maquette_url": a.maquette_url or "",
                 "notes": a.notes or ""}
        ajouter_ligne(chemin, ENTETE_LEDGER, ligne)
    return 0, {"ok": True, "action": "add", "ligne": ligne}


def cmd_set(a, data_dir):
    if a.statut and a.statut not in STATUTS:
        return 2, {"ok": False, "erreur": f"statut inconnu « {a.statut} »"}
    dom, em = norm_domaine(a.domaine), norm_email(a.email)
    if not (dom or em):
        return 2, {"ok": False, "erreur": "--domaine ou --email requis"}
    champs = {k: getattr(a, k) for k in ("statut", "thread_id", "draft_id", "maquette_url", "notes") if getattr(a, k) is not None}
    if not champs:
        return 2, {"ok": False, "erreur": "rien à modifier"}
    chemin = os.path.join(data_dir, "ledger.csv")
    with verrou(data_dir):
        lignes = lire(chemin, ENTETE_LEDGER)
        modif = []
        for r in lignes:
            if (dom and r["domaine"] == dom) or (em and r["email"] == em):
                for k, v in champs.items():
                    if k == "notes" and a.ajouter_note and r["notes"]:
                        r["notes"] = f"{r['notes']} | {v}"
                    else:
                        r[k] = v
                modif.append(r)
        if not modif:
            return 1, {"ok": False, "erreur": "aucune ligne trouvée pour cet identifiant"}
        ecrire_tout(chemin, ENTETE_LEDGER, lignes)
    return 0, {"ok": True, "action": "set", "modifiees": len(modif), "lignes": modif}


def _opposition_match(data_dir, dom, em, si):
    res = []
    for r in lire(os.path.join(data_dir, "opposition.csv"), ENTETE_OPPOSITION):
        v, t = r["valeur"].lower(), (r["type"] or type_valeur(r["valeur"].lower())).lower()
        if t == "bounce":
            t = "email"  # une adresse en erreur de distribution se compare comme un e-mail
        if t == "siren" and si and v == si:
            res.append(r)
        elif t == "email" and em and v == em:
            res.append(r)
        elif t == "email" and dom and "@" in v and v.split("@", 1)[1] == dom and dom not in WEBMAILS:
            res.append(r)  # opposition d'une adresse sur le domaine propre de l'entreprise : vaut pour le domaine
        elif t == "domaine" and dom and norm_domaine(v) == dom:
            res.append(r)
    return res


def cmd_check(a, data_dir):
    dom, em = norm_domaine(a.domaine), norm_email(a.email)
    if not (dom or em):
        return 2, {"ok": False, "erreur": "--email ou --domaine requis"}
    if em and not dom and em.split("@", 1)[1] not in WEBMAILS:
        dom_email = em.split("@", 1)[1]
    else:
        dom_email = ""
    lignes = [r for r in lire(os.path.join(data_dir, "ledger.csv"), ENTETE_LEDGER)
              if (dom and r["domaine"] == dom) or (em and r["email"] == em) or (dom_email and r["domaine"] == dom_email)]
    opp = _opposition_match(data_dir, dom or dom_email, em, "")
    statuts = {r["statut"] for r in lignes}
    bloque = bool(opp) or bool(statuts & {"stop", "bounced", "won", "lost", "sent", "replied", "interested", "drafted"})
    motif = ("opposition" if opp else ("statut " + ", ".join(sorted(statuts & {"stop", "bounced", "won", "lost", "sent", "replied", "interested", "drafted"}))
                                       if bloque else ""))
    return 0, {"ok": True, "action": "check", "domaine": dom or dom_email, "email": em, "trouve": bool(lignes),
               "contact_autorise": not bloque, "motif_blocage": motif, "ledger": lignes, "opposition": opp}


def cmd_stop(a, data_dir):
    v = (a.valeur or "").strip().lower()
    if not v:
        return 2, {"ok": False, "erreur": "--valeur requis"}
    t = type_valeur(v, a.type)
    statut_cible = "bounced" if t == "bounce" else "stop"
    t_cmp = "email" if t == "bounce" else t
    if t == "domaine":
        v = norm_domaine(v)
    if t == "siren":
        v = norm_siren(v)
    chemin_opp = os.path.join(data_dir, "opposition.csv")
    with verrou(data_dir):
        deja = [r for r in lire(chemin_opp, ENTETE_OPPOSITION) if r["valeur"].lower() == v]
        if not deja:
            ajouter_ligne(chemin_opp, ENTETE_OPPOSITION, {"valeur": v, "type": t, "date": date.today().isoformat(), "source": a.source})
        chemin = os.path.join(data_dir, "ledger.csv")
        lignes = lire(chemin, ENTETE_LEDGER)
        n = 0
        dom_email = v.split("@", 1)[1] if t_cmp == "email" and "@" in v and v.split("@", 1)[1] not in WEBMAILS else ""
        for r in lignes:
            if (t_cmp == "email" and (r["email"] == v or (dom_email and r["domaine"] == dom_email))) or \
               (t_cmp == "domaine" and r["domaine"] == v) or (t_cmp == "siren" and r["siren"] == v):
                if r["statut"] not in ("stop", statut_cible):
                    r["statut"] = statut_cible
                    r["notes"] = (r["notes"] + " | " if r["notes"] else "") + f"{statut_cible} {date.today().isoformat()} ({a.source})"
                    n += 1
        if n:
            ecrire_tout(chemin, ENTETE_LEDGER, lignes)
    return 0, {"ok": True, "action": "stop", "valeur": v, "type": t, "statut_applique": statut_cible, "deja_en_opposition": bool(deja),
               "lignes_ledger_modifiees": n}


def cmd_list(a, data_dir):
    lignes = lire(os.path.join(data_dir, "ledger.csv"), ENTETE_LEDGER)
    if a.statut:
        lignes = [r for r in lignes if r["statut"] == a.statut]
    compte = {}
    for r in lignes:
        compte[r["statut"]] = compte.get(r["statut"], 0) + 1
    return 0, {"ok": True, "action": "list", "total": len(lignes), "par_statut": compte, "lignes": lignes}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", default=DATA_DEFAUT)
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("add"); s.add_argument("--siren"); s.add_argument("--domaine"); s.add_argument("--email")
    s.add_argument("--statut", default="queued"); s.add_argument("--thread_id"); s.add_argument("--draft_id")
    s.add_argument("--maquette_url"); s.add_argument("--notes"); s.add_argument("--force", action="store_true")
    s = sp.add_parser("set"); s.add_argument("--domaine"); s.add_argument("--email"); s.add_argument("--statut")
    s.add_argument("--thread_id"); s.add_argument("--draft_id"); s.add_argument("--maquette_url"); s.add_argument("--notes")
    s.add_argument("--ajouter-note", action="store_true", help="concatène la note au lieu de la remplacer")
    s = sp.add_parser("check"); s.add_argument("--email"); s.add_argument("--domaine")
    s = sp.add_parser("stop"); s.add_argument("--valeur", required=True); s.add_argument("--source", required=True)
    s.add_argument("--type", choices=["email", "domaine", "siren", "bounce"])
    s = sp.add_parser("list"); s.add_argument("--statut")
    a = p.parse_args(argv)
    data_dir = os.path.abspath(a.data_dir)
    try:
        with verrou(data_dir):
            creer_si_absent(os.path.join(data_dir, "ledger.csv"), ENTETE_LEDGER)
            creer_si_absent(os.path.join(data_dir, "opposition.csv"), ENTETE_OPPOSITION)
        code, res = {"add": cmd_add, "set": cmd_set, "check": cmd_check, "stop": cmd_stop, "list": cmd_list}[a.cmd](a, data_dir)
    except (OSError, csv.Error) as e:
        code, res = 2, {"ok": False, "erreur": f"{type(e).__name__} : {e}"}
    print(json.dumps(res, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
