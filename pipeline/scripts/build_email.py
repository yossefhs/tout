#!/home/user/.venv-webtest/bin/python
"""build_email.py — rédige l'e-mail de prospection (texte brut) à partir d'un audit et d'un lead.

Usage :
  build_email.py --audit audit.json --lead lead.json --config config.json [--maquette-url URL]
                 --out <dossier>/email.json [--phrases templates/email_phrases.json] [--graine N]

Entrées :
  audit.json : sortie d'audit_site.py (analyse.constats [{id,type,gravite,titre,preuve,…}], analyse.verdict, cible)
  lead.json  : une ligne de data/queue.csv en JSON (nom, enseigne, ville, site, email, tel, siren…)
  config.json : clé « expediteur » (nom, entreprise, email, tel, adresse, url_offre, url_confidentialite) ;
                valeurs par défaut Clients Ici si la clé manque.

Sortie : email.json (objets[2], corps, signature, bloc_information, texte_complet, nb_mots_corps,
constats_utilises, whatsapp, sms, controles) + email.txt à côté. Une ligne JSON de résumé sur stdout.
Règles : corps 80 à 110 mots (compteur interne compter_mots : un mot = suite de lettres/chiffres, apostrophes et
traits d'union internes compris ; ponctuation et guillemets ignorés ; une URL compte un mot par segment), 1 à 2 constats
parmi les plus graves, mention de la maquette seulement si --maquette-url, une seule question, pas de HTML, pas de
pixel, pas de lien raccourci, aucun chiffre (donc jamais de score ni de mesure Lighthouse : la lenteur est un constat
sans chiffre), aucune prétention de visite humaine (« je suis passé… », « depuis mon téléphone »), pas de « site
vitrine » dans les objets (on ne sait pas si c'en est un).
Codes : 0 écrit ; 2 arguments/fichiers invalides ; 3 aucun constat exploitable (pas d'e-mail à écrire).
"""
import argparse
import hashlib
import itertools
import json
import os
import random
import re
import sys
import tempfile
from datetime import date

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
PHRASES_DEFAUT = os.path.join(PIPELINE, "templates", "email_phrases.json")

EXPEDITEUR_DEFAUT = {
    "nom": "Guillaume Samama",
    "entreprise": "Clients Ici",
    "email": "contact@clientsici.fr",
    "tel": "07 56 97 45 75",
    "adresse": "6 rue du Parc, 28190 Landelles",
    "url_offre": "https://clientsici.fr/refonte-site-vitrine/",
    "url_confidentialite": "https://clientsici.fr/confidentialite/",
}
GRAVITE_RANG = {"haute": 0, "moyenne": 1, "basse": 2}
MOTS_MIN, MOTS_MAX = 80, 110
MOTS_CIBLE = 95
# Formulations interdites : prétention de visite humaine ou de constat « de visu », chiffres/mesures d'outil.
MOTIFS_VISITE = re.compile(r"je suis pass[ée]|je suis venu|pass[ée] (?:chez vous|devant|en boutique|à l'atelier|au magasin)"
                           r"|visit[ée] (?:votre|vos|la boutique|l'atelier|le magasin)|sur place|depuis mon (?:téléphone|portable|mobile)"
                           r"|sur mon (?:téléphone|portable|mobile)", re.I)
MOTIFS_MESURE = re.compile(r"lighthouse|pagespeed|\bscore|/100|\d\s*(?:s|ms|secondes?)\b|\d\s*%", re.I)
MOTIFS_OBJET_INTERDITS = re.compile(r"site vitrine|urgent|!!|\?\?", re.I)
MARQUE_BROUILLON = "brouillon — conditions de contact à vérifier"


def charger_json(chemin, nom):
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"{nom} illisible ({chemin}) : {e}")
    if not isinstance(d, dict):
        raise ValueError(f"{nom} : un objet JSON est attendu")
    return d


def domaine_de(url):
    if not url:
        return None
    m = re.match(r"^(?:https?://)?([^/:?#]+)", str(url).strip(), re.I)
    return m.group(1).lower().removeprefix("www.") if m else None


MOT = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)


def compter_mots(texte):
    """Compteur interne (documenté dans docs/03) : un mot = une suite de lettres ou de chiffres, les apostrophes et
    traits d'union internes liant les morceaux (« l'adresse » = 1, « Nogent-le-Rotrou » = 1) ; ponctuation, guillemets
    et tirets isolés ne comptent pas ; une URL compte un mot par segment (https, domaine, dossier…)."""
    return len(MOT.findall(texte)) if texte else 0


def categoriser(titre, cats):
    for nom, c in cats.items():
        for motif in c.get("motifs", []):
            if re.search(motif, titre or "", re.I):
                return nom
    return None


def choisir_constats(audit, phrases):
    """Constats triés par gravité, catégorisés ; exclut les constats « information » et non exploitables."""
    constats = (audit.get("analyse") or {}).get("constats") or []
    exclus = phrases.get("categories_exclues", [])
    cats = phrases["categories"]
    utilisables = []
    for c in constats:
        if not isinstance(c, dict):
            continue
        titre = c.get("titre") or ""
        if any(e.lower() in titre.lower() for e in exclus):
            continue
        cat = categoriser(titre, cats)
        if not cat:
            continue
        utilisables.append({"id": c.get("id"), "gravite": c.get("gravite", "basse"), "titre": titre, "categorie": cat,
                            "preuve": (c.get("preuve") or {}).get("valeur")})
    utilisables.sort(key=lambda x: (GRAVITE_RANG.get(x["gravite"], 3), x["id"] or ""))
    # une seule catégorie par e-mail (pas deux phrases sur la vitesse, par exemple)
    vus, res = set(), []
    for u in utilisables:
        if u["categorie"] in vus:
            continue
        vus.add(u["categorie"])
        res.append(u)
    return res


def decapitaliser(phrase):
    """Première lettre en minuscule (les phrases de constat suivent « … relevé : »)."""
    return phrase[:1].lower() + phrase[1:] if phrase and not phrase.startswith("«") else phrase


def composer_corps(rng, phrases, ctx, constats, maquette_url):
    """Essaie des combinaisons de variantes et renvoie (corps, nb_mots, constats_utilises, avertissement)."""
    cats = phrases["categories"]
    sal = rng.choice(phrases["salutations"])
    ouvertures = phrases["ouvertures"][:]
    benefices = phrases["benefices"][:]
    maqs = (phrases["maquette_avec_url"] if maquette_url else phrases["maquette_sans_url"])[:]
    questions = (phrases["questions_avec_url"] if maquette_url else phrases["questions_sans_url"])[:]
    liaisons = phrases["liaisons"][:]
    for liste in (ouvertures, benefices, maqs, questions, liaisons):
        rng.shuffle(liste)
    c1 = constats[0]
    c2 = constats[1] if len(constats) > 1 else None
    var1 = cats[c1["categorie"]]["constats"][:]
    var2 = cats[c2["categorie"]]["constats"][:] if c2 else [None]
    rng.shuffle(var1)
    if c2:
        rng.shuffle(var2)

    def fmt(s):
        return s.format(**ctx)

    candidats = []
    # d'abord avec deux constats (plus précis), puis avec un seul
    for avec_deux in ([True, False] if c2 else [False]):
        for o, v1, v2, li, b, m, q in itertools.product(ouvertures, var1, var2 if avec_deux else [None],
                                                        liaisons if avec_deux else [None], benefices, maqs, questions):
            p1 = f"{fmt(o)} {v1[:1].upper() + v1[1:]}"
            if avec_deux:
                p1 += f" {li} {v2}"
            corps = "\n\n".join([sal, p1, fmt(b), fmt(m), q])
            n = compter_mots(corps)
            candidats.append((abs(n - MOTS_CIBLE), 0 if avec_deux else 1, n, corps, avec_deux))
    # première combinaison dans la plage, dans l'ordre (mélangé par la graine) : varie d'un lead à l'autre
    dans_plage = [c for c in candidats if MOTS_MIN <= c[2] <= MOTS_MAX]
    if dans_plage:
        _, _, n, corps, deux = dans_plage[0]
        return corps, n, [c1] + ([c2] if deux else []), None
    candidats.sort(key=lambda c: (c[0], c[1]))
    _, _, n, corps, deux = candidats[0]
    return corps, n, [c1] + ([c2] if deux else []), f"aucune combinaison entre {MOTS_MIN} et {MOTS_MAX} mots ; {n} mots retenus"


def composer_objets(rng, phrases, ctx, constats):
    cats = phrases["categories"]
    pool = []
    for c in constats:
        pool += cats[c["categorie"]].get("objets", [])
    pool += phrases["objets_generiques"]
    objets, vus = [], set()
    ordre = pool[:]
    rng.shuffle(ordre)
    for o in ordre:
        s = o.format(**ctx).strip()
        if len(s) > 50 or s.lower() in vus or MOTIFS_OBJET_INTERDITS.search(s):
            continue
        if sum(1 for ch in s if ch.isupper()) > max(3, len(s) // 4):
            continue
        if s and s[0].islower() and '.' not in s.split()[0]:
            s = s[0].upper() + s[1:]
        objets.append(s)
        vus.add(s.lower())
        if len(objets) == 2:
            break
    secours = ["Un point sur votre site", f"{ctx['domaine']} sur téléphone"[:50], "Votre site sur téléphone"]
    while len(objets) < 2:
        objets.append(next((o for o in secours if o not in objets), "votre site"))
    return objets


def signature(exp):
    return "\n".join([exp["nom"], exp["entreprise"], exp["url_offre"], exp["email"], exp["adresse"]])


def bloc_information(exp, domaine):
    return "\n".join([
        f"Pourquoi ce message : vos coordonnées viennent de votre site {domaine}, qui est public.",
        "Pour ne plus recevoir de message, répondez STOP et je vous retire de ma liste.",
        f"Confidentialité : {exp['url_confidentialite']}",
    ])


def controler(objets, corps, maquette_url, domaine, autres_textes=()):
    """Contrôles de forme ; autres_textes (WhatsApp, SMS) ne sont vérifiés que pour la prétention de visite."""
    pb = []
    for o in objets:
        if len(o) > 50:
            pb.append(f"objet trop long : {o}")
        if "urgent" in o.lower():
            pb.append(f"objet contient « urgent » : {o}")
        if "site vitrine" in o.lower():
            pb.append(f"objet affirme « site vitrine » sans le savoir : {o}")
    n = compter_mots(corps)
    if not (MOTS_MIN <= n <= MOTS_MAX):
        pb.append(f"corps de {n} mots (attendu {MOTS_MIN}–{MOTS_MAX})")
    if re.search(r"<[a-z][^>]*>", corps):
        pb.append("balise HTML dans le corps")
    if "—" in corps:
        pb.append("tiret cadratin dans le corps")
    sans_url = corps.replace(maquette_url or "", "").replace(domaine or "", "")
    if re.search(r"https?://|www\.", sans_url):
        pb.append("lien non prévu dans le corps")
    if re.search(r"\d", sans_url):
        pb.append("chiffre dans le corps (aucun chiffre promis)")
    if corps.count("?") != 1:
        pb.append(f"{corps.count('?')} question(s) dans le corps (attendu : 1)")
    if re.search(r"bit\.ly|tinyurl|t\.co/|goo\.gl", corps, re.I):
        pb.append("lien raccourci")
    m = MOTIFS_MESURE.search(sans_url)
    if m:
        pb.append(f"mesure ou score d'outil dans le corps : « {m.group(0)} »")
    for nom_txt, t in [("corps", corps)] + [(f"texte {i + 1}", x) for i, x in enumerate(autres_textes)]:
        m = MOTIFS_VISITE.search(t or "")
        if m:
            pb.append(f"prétention de visite humaine ({nom_txt}) : « {m.group(0)} »")
    return pb


def ecrire_atomique(chemin, contenu):
    dossier = os.path.dirname(os.path.abspath(chemin)) or "."
    os.makedirs(dossier, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".email-", suffix=".tmp", dir=dossier)
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
    p.add_argument("--audit", required=True)
    p.add_argument("--lead", required=True)
    p.add_argument("--config", default=os.path.join(PIPELINE, "config.json"))
    p.add_argument("--maquette-url", default=None)
    p.add_argument("--out", required=True, help="chemin de email.json")
    p.add_argument("--phrases", default=PHRASES_DEFAUT)
    p.add_argument("--graine", type=int, default=None, help="graine aléatoire (défaut : dérivée du domaine)")
    a = p.parse_args(argv)

    try:
        audit = charger_json(a.audit, "audit")
        lead = charger_json(a.lead, "lead")
        phrases = charger_json(a.phrases, "banque de phrases")
        if not isinstance(phrases.get("categories"), dict):
            raise ValueError("banque de phrases : clé « categories » absente")
        cfg = charger_json(a.config, "config") if os.path.exists(a.config) else {}
    except ValueError as e:
        print(json.dumps({"ok": False, "erreur": str(e)}, ensure_ascii=False))
        return 2
    exp = dict(EXPEDITEUR_DEFAUT)
    exp.update({k: v for k, v in (cfg.get("expediteur") or {}).items() if isinstance(v, str) and v.strip()})

    if a.maquette_url and not re.match(r"^https://[^\s]+$", a.maquette_url):
        print(json.dumps({"ok": False, "erreur": "--maquette-url doit être une URL https complète"}, ensure_ascii=False))
        return 2

    cible = audit.get("cible") or {}
    domaine = (domaine_de(cible.get("url_finale")) or domaine_de(cible.get("url_demandee"))
               or domaine_de(lead.get("site")) or domaine_de(((audit.get("meta") or {}).get("parametres") or {}).get("url")))
    if not domaine:
        print(json.dumps({"ok": False, "erreur": "domaine introuvable (audit.cible ou lead.site)"}, ensure_ascii=False))
        return 2
    nom = (lead.get("enseigne") or lead.get("nom") or domaine).strip()
    ville = (lead.get("ville") or "").strip()
    ctx = {"domaine": domaine, "nom": nom, "ville": ville, "url": a.maquette_url or ""}

    constats = choisir_constats(audit, phrases)
    verdict = (audit.get("analyse") or {}).get("verdict")
    if not constats or verdict == "informations insuffisantes":
        print(json.dumps({"ok": False, "erreur": "aucun constat exploitable : pas d'e-mail à écrire",
                          "verdict": verdict, "domaine": domaine}, ensure_ascii=False))
        return 3

    graine = a.graine if a.graine is not None else int(hashlib.sha256(domaine.encode()).hexdigest()[:8], 16)
    rng = random.Random(graine)
    corps, nb_mots, utilises, avert = composer_corps(rng, phrases, ctx, constats, a.maquette_url)
    objets = composer_objets(rng, phrases, ctx, utilises)
    sig = signature(exp)
    info = bloc_information(exp, domaine)
    texte = f"{corps}\n\n{sig}\n\n--\n{info}\n"

    court = phrases["categories"][utilises[0]["categorie"]]["courts"][0].format(**ctx)
    wa = rng.choice(phrases["whatsapp"]).format(constat_court=court, **ctx)
    sms = rng.choice(phrases["sms"]).format(constat_court=court, **ctx)

    problemes = controler(objets, corps, a.maquette_url, domaine, autres_textes=(wa, sms))
    avertissements = [x for x in [avert] if x]
    resultat = {
        "version": "1.0", "date": date.today().isoformat(), "graine": graine,
        "lead": {"siren": lead.get("siren"), "nom": nom, "domaine": domaine, "email": lead.get("email"), "ville": ville},
        "objets": objets, "corps": corps, "signature": sig, "bloc_information": info, "texte_complet": texte,
        "nb_mots_corps": nb_mots, "nb_mots_total": compter_mots(texte),
        "constats_utilises": [{k: c[k] for k in ("id", "categorie", "gravite", "titre")} for c in utilises],
        "constats_disponibles": len(constats), "verdict_audit": verdict,
        "maquette_url": a.maquette_url,
        "whatsapp": {"texte": wa, "statut": MARQUE_BROUILLON, "nb_caracteres": len(wa)},
        "sms": {"texte": sms, "statut": MARQUE_BROUILLON, "nb_caracteres": len(sms)},
        "controles": {"ok": not problemes, "problemes": problemes},
        "avertissements": avertissements,
        "format": "text/plain", "suivi": "aucun pixel, aucun lien raccourci",
    }
    ecrire_atomique(a.out, json.dumps(resultat, ensure_ascii=False, indent=2) + "\n")
    txt = os.path.join(os.path.dirname(os.path.abspath(a.out)), "email.txt")
    ecrire_atomique(txt, f"Objet 1 : {objets[0]}\nObjet 2 : {objets[1]}\n\n{texte}")
    print(json.dumps({"ok": not problemes, "out": os.path.abspath(a.out), "objets": objets, "nb_mots_corps": nb_mots,
                      "constats": [c["id"] for c in utilises], "problemes": problemes, "avertissements": avertissements},
                     ensure_ascii=False))
    return 0 if not problemes else 1


if __name__ == "__main__":
    sys.exit(main())
