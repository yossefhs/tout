#!/usr/bin/env python3
"""filter_queue.py — transforme un CSV enrichi (enrich.js) en file de prospection data/queue.csv.

Usage :
  filter_queue.py <enrichis.csv> [<autre.csv> ...] [--out data/queue.csv] [--data-dir data]
                  [--rejets data/queue_rejets.csv] [--ajouter] [--config config.json]

Règles (voir docs/01-leads.md) :
  - cible TPE (config.json « cible_tpe ») : exclure les entreprises hors cible, motif « hors_cible_taille » :
    tranche d'effectif INSEE > effectif_max_code (codes 00,01,02,03,11,12,21… ; 11 = 10 à 19 salariés ;
    effectif vide ou NN = gardé), CA > ca_max, établissements ouverts > nb_etablissements_max, ou un motif de
    motifs_exclus_nom (mot entier) dans le nom ou l'enseigne (GROUPE, HOLDING…) ;
  - garder seulement : site présent ET site_confiance ∈ {haute, moyenne} ET e-mail présent ;
  - dédoublonner par domaine du site (le lead au meilleur score_lead gagne) ;
  - exclure les domaines / e-mails / SIREN listés dans data/opposition.csv (valeur;type;date;source)
    et déjà présents dans data/ledger.csv (date;siren;domaine;email;statut;thread_id;draft_id;maquette_url;notes) ;
    les deux fichiers sont créés vides (avec en-tête) s'ils manquent ;
  - typer l'e-mail : generique | nominatif | webmail. Les webmails (orange, gmail, free…) sont conservés :
    ce sont des TPE. Sont exclues uniquement les adresses manifestement personnelles :
    webmail + partie locale qui est un nom de personne (dirigeant connu, ou prénom.nom).
  - par défaut la file est RÉÉCRITE ; --ajouter fusionne avec la file existante (dédoublonnage par domaine).

Sortie : data/queue.csv (séparateur ; UTF-8 avec BOM), data/queue_rejets.csv (motifs d'exclusion),
         et un résumé JSON sur stdout. Code retour 0 même si la file est vide (le résumé le dit).
"""
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import date
from urllib.parse import urlsplit

csv.field_size_limit(10_000_000)

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)

COLONNES_QUEUE = [
    "siren", "nom", "enseigne", "naf", "libelle_naf", "adresse", "cp", "ville", "dept", "dirigeants",
    "site", "site_confiance", "email", "email_type", "tel", "score_lead", "date_collecte",
]
COLONNES_REJETS = ["date", "siren", "nom", "ville", "site", "site_confiance", "email", "motif"]
ENTETE_OPPOSITION = ["valeur", "type", "date", "source"]
ENTETE_LEDGER = ["date", "siren", "domaine", "email", "statut", "thread_id", "draft_id", "maquette_url", "notes"]

WEBMAILS = {
    "gmail.com", "googlemail.com", "hotmail.fr", "hotmail.com", "hotmail.co.uk", "outlook.fr", "outlook.com",
    "live.fr", "live.com", "msn.com", "yahoo.fr", "yahoo.com", "ymail.com", "rocketmail.com",
    "orange.fr", "wanadoo.fr", "free.fr", "sfr.fr", "neuf.fr", "cegetel.net", "club-internet.fr",
    "laposte.net", "bbox.fr", "numericable.fr", "numericable.com", "aliceadsl.fr", "alice.fr",
    "aol.com", "aol.fr", "icloud.com", "me.com", "mac.com", "protonmail.com", "proton.me", "pm.me",
    "gmx.fr", "gmx.com", "gmx.net", "nordnet.fr", "9online.fr", "voila.fr", "libertysurf.fr", "tiscali.fr",
    "dbmail.com", "hotmail.de", "yandex.com", "yandex.ru", "mail.com", "zoho.com", "ovh.fr", "noos.fr",
    "modulonet.fr", "akeonet.com", "wibox.fr", "netcourrier.com", "mailo.com", "lilo.org",
}

LOCAUX_GENERIQUES = {
    "contact", "contacts", "info", "infos", "information", "informations", "bonjour", "hello", "accueil",
    "commercial", "commerciale", "secretariat", "administration", "admin", "direction", "devis", "compta",
    "comptabilite", "facturation", "factures", "facture", "sav", "support", "bureau", "agence", "entreprise",
    "societe", "ste", "vente", "ventes", "boutique", "atelier", "magasin", "mail", "email", "courrier",
    "communication", "com", "rh", "recrutement", "sales", "office", "service", "services", "serviceclient",
    "service-client", "clientele", "client", "clients", "reservation", "reservations", "resa", "commande",
    "commandes", "webmaster", "postmaster", "hostmaster", "noreply", "no-reply", "nepasrepondre", "team",
    "equipe", "pro", "gestion", "siege", "standard", "contactez-nous", "contact-us", "demande", "demandes",
    "salon", "cabinet", "garage", "restaurant", "resto", "boulangerie", "patisserie", "coiffure", "plomberie",
    "plombier", "chauffage", "electricite", "elec", "menuiserie", "peinture", "couverture", "maconnerie",
    "travaux", "renovation", "batiment", "btp", "artisan", "artisans", "entreprises", "ets", "sarl", "sas",
    "eurl", "direction-generale", "dg", "president", "gerant", "gerance", "mairie", "secretaire",
}

# Prénoms français fréquents (pour détecter "prenom.nom@webmail" sans dirigeant connu)
PRENOMS = set("""
alain albert alexandre alexis alice amandine amelie anais andre anne annie anthony antoine arnaud arthur
aurelie aurelien axel baptiste bastien beatrice benjamin benoit bernard bertrand brigitte bruno camille
carole caroline catherine cedric celine chantal charles charlotte chloe christelle christian christiane
christine christophe claire claude clement colette corinne cyril damien daniel daniele david delphine denis
didier dominique dylan edouard elisabeth elise elodie emeline emilie emma emmanuel enzo eric estelle etienne
eva fabien fabienne fabrice fanny florence florent florian francis francois francoise franck frederic
frederique gabriel gaelle gaetan gautier genevieve geoffrey georges gerald gerard ghislaine gilbert gilles
gregory guillaume guy helene henri herve hugo isabelle jacky jacqueline jacques jean jeanne jennifer jeremie
jeremy jerome jessica joel johan jonathan jordan joseph josette josiane julie julien juliette justine karine
kevin laetitia laura laure laurence laurent lea leo lionel loic louis luc lucas lucie ludovic manon marc
marcel margaux marie marine marion martine mathieu mathilde matthieu maurice maxime melanie michel micheline
michele mickael monique morgane muriel myriam nadia nadine nathalie nathan nicolas nicole noel olivier
pascal pascale patrice patricia patrick paul pauline philippe pierre quentin raphael raymond regis remi remy
renaud rene richard robert roger roland romain sabrina samuel sandra sandrine sarah sebastien serge severine
simon sophie stephane stephanie sylvain sylvie theo thierry thomas valentin valerie vanessa veronique victor
vincent virginie william xavier yann yannick yves yvette yvonne zoe mohamed mehdi karim samir rachid nabil
mustapha ahmed ali omar youssef said farid hakim malik sofiane yanis ines sarah leila nadia fatima
""".split())


CIBLE_TPE_DEFAUT = {"effectif_max_code": "11", "ca_max": 2000000, "nb_etablissements_max": 2,
                    "motifs_exclus_nom": ["GROUPE", "HOLDING", "SAS INTERNATIONAL"]}


def charger_cible_tpe(chemin_config):
    """Lit « cible_tpe » dans config.json (valeurs par défaut pour les sous-clés absentes ; fichier absent toléré)."""
    cible = dict(CIBLE_TPE_DEFAUT)
    if chemin_config and os.path.exists(chemin_config):
        try:
            with open(chemin_config, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"  (config illisible, cible TPE par défaut : {e})", file=sys.stderr)
            cfg = {}
        c = cfg.get("cible_tpe") if isinstance(cfg, dict) else None
        if isinstance(c, dict):
            cible.update({k: v for k, v in c.items() if k in CIBLE_TPE_DEFAUT and v is not None})
    cible["motifs_exclus_nom"] = [str(m) for m in (cible.get("motifs_exclus_nom") or []) if str(m).strip()]
    return cible


def _nombre(v):
    """'47311065' / '4.7e7' → float ; vide, NN ou non numérique → None."""
    v = str(v or "").strip().replace(" ", "").replace(",", ".")
    if not v:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def hors_cible_taille(lead, cible):
    """Renvoie le détail du dépassement (« effectif=22,ca=47311065 ») si l'entreprise sort de la cible TPE, sinon None.
    Un champ vide ou non renseigné (effectif NN, CA absent) ne fait jamais rejeter : on garde."""
    motifs = []
    eff = (lead.get("effectif") or "").strip()
    eff_max = str(cible.get("effectif_max_code") or "").strip()
    if eff.isdigit() and eff_max.isdigit() and int(eff) > int(eff_max):
        motifs.append(f"effectif={eff}")
    ca = _nombre(lead.get("ca"))
    ca_max = _nombre(cible.get("ca_max"))
    if ca is not None and ca_max is not None and ca > ca_max:
        motifs.append(f"ca={int(ca)}")
    nb = _nombre(lead.get("nb_etablissements"))
    nb_max = _nombre(cible.get("nb_etablissements_max"))
    if nb is not None and nb_max is not None and nb > nb_max:
        motifs.append(f"nb_etablissements={int(nb)}")
    texte = norm(f"{lead.get('nom', '')} {lead.get('enseigne', '')}")
    for m in cible.get("motifs_exclus_nom") or []:
        mn = norm(m)
        if mn and re.search(r"(?<![a-z0-9])" + re.escape(mn) + r"(?![a-z0-9])", texte):
            motifs.append(f"nom~{m}")
    return ",".join(motifs) if motifs else None


PLACEHOLDER_DOMAINES = {"email.fr", "email.com", "exemple.fr", "exemple.com", "example.com", "example.fr", "example.org",
                        "test.fr", "test.com", "domaine.fr", "votredomaine.fr", "monsite.fr", "site.fr", "mail.fr", "mon-domaine.fr",
                        "sentry.io", "wixpress.com", "clientsici.fr"}


def charger_annuaires():
    """Domaines d'annuaires (scripts/annuaires.txt) : un site hébergé là n'est pas le site propre de l'entreprise."""
    chemin = os.path.join(ICI, "annuaires.txt")
    doms = set()
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            for l in f:
                d = l.strip().lower()
                if d and not d.startswith("#"):
                    doms.add(d[4:] if d.startswith("www.") else d)
    return doms


ANNUAIRES = charger_annuaires()


def est_annuaire(domaine):
    d = (domaine or "").lower()
    return any(d == a or d.endswith("." + a) for a in ANNUAIRES)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def norm(s):
    return strip_accents(str(s or "")).lower().strip()


def domaine_site(url):
    if not url:
        return ""
    u = url.strip()
    if "://" not in u:
        u = "https://" + u
    try:
        host = urlsplit(u).hostname or ""
    except ValueError:
        return ""
    host = host.lower()
    return host[4:] if host.startswith("www.") else host


def domaine_email(email):
    return email.rsplit("@", 1)[1].lower() if "@" in email else ""


def tokens_dirigeants(dirigeants):
    """'Jean DUPONT (Gérant) | Marie MARTIN (Associé)' → {'jean', 'dupont', 'marie', 'martin'}"""
    txt = re.sub(r"\([^)]*\)", " ", norm(dirigeants))
    return {t for t in re.split(r"[^a-z]+", txt) if len(t) >= 3}


def tokens_nom(nom, enseigne):
    txt = re.sub(r"\([^)]*\)", " ", norm(f"{nom} {enseigne}"))
    return {t for t in re.split(r"[^a-z0-9]+", txt) if len(t) >= 3}


def typer_email(email, lead):
    """→ (email_type, personnel: bool). personnel = manifestement l'adresse privée d'une personne."""
    local, _, dom = email.lower().partition("@")
    local_n = norm(local)
    parts = [p for p in re.split(r"[._\-]+", local_n) if p]
    t_dir = tokens_dirigeants(lead.get("dirigeants", ""))
    t_nom = tokens_nom(lead.get("nom", ""), lead.get("enseigne", ""))
    local_alpha = re.sub(r"[^a-z]", "", local_n)

    generique = local_n in LOCAUX_GENERIQUES or any(p in LOCAUX_GENERIQUES for p in parts if len(parts) == 1)
    # partie locale = nom de l'entreprise (ex : plomberie-martin@orange.fr, pmartinsarl@…)
    nom_entreprise = bool(t_nom) and (any(p in t_nom for p in parts) or any(t in local_alpha for t in t_nom if len(t) >= 5))
    # partie locale = nom d'une personne
    match_dirigeant = any(p in t_dir for p in parts if len(p) >= 3) or any(t in local_alpha for t in t_dir if len(t) >= 5)
    prenom_nom = (len(parts) == 2 and parts[0] in PRENOMS and parts[1].isalpha() and parts[1] not in LOCAUX_GENERIQUES) \
        or (len(parts) == 1 and any(local_alpha.startswith(p) and len(local_alpha) > len(p) + 2 for p in PRENOMS if len(p) >= 4))
    initiale_nom = len(parts) == 2 and len(parts[0]) == 1 and parts[1].isalpha() and len(parts[1]) >= 3
    nominatif = match_dirigeant or prenom_nom or initiale_nom

    # Pour une TPE, « dupont@dupont-plomberie.fr » est l'adresse de l'entreprise : le nom du dirigeant
    # est souvent le nom de la société. On ne le traite pas comme personnel.
    if dom in WEBMAILS:
        personnel = nominatif and not nom_entreprise and not generique
        return "webmail", personnel
    if generique or nom_entreprise and not match_dirigeant:
        return "generique", False
    if nominatif:
        return "nominatif", False
    return "generique", False


def charger_liste(chemin, entete):
    """Crée le fichier avec son en-tête s'il manque ; renvoie les lignes (dict)."""
    if not os.path.exists(chemin) or os.path.getsize(chemin) == 0:
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8", newline="") as f:
            csv.writer(f, delimiter=";", lineterminator="\n").writerow(entete)
        return []
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def ensembles_exclusion(data_dir):
    opp = charger_liste(os.path.join(data_dir, "opposition.csv"), ENTETE_OPPOSITION)
    led = charger_liste(os.path.join(data_dir, "ledger.csv"), ENTETE_LEDGER)
    domaines, emails, sirens = set(), set(), set()
    for r in opp:
        v = (r.get("valeur") or "").strip().lower()
        t = (r.get("type") or "").strip().lower()
        if not v:
            continue
        if t == "siren" or (t == "" and v.isdigit() and len(v) == 9):
            sirens.add(v)
        elif t == "email" or (t == "" and "@" in v):
            emails.add(v)
            # un e-mail sur un domaine propre à l'entreprise vaut opposition pour tout le domaine,
            # sauf s'il s'agit d'un webmail partagé par des milliers de TPE
            d = domaine_email(v)
            if d and d not in WEBMAILS:
                domaines.add(d)
        else:
            domaines.add(domaine_site(v) or v)
    for r in led:
        d = domaine_site((r.get("domaine") or "").strip())
        e = (r.get("email") or "").strip().lower()
        s = (r.get("siren") or "").strip()
        if d:
            domaines.add(d)
        if e:
            emails.add(e)
        if s:
            sirens.add(s)
    return {"domaines": domaines, "emails": emails, "sirens": sirens, "n_opposition": len(opp), "n_ledger": len(led)}


def premier(s, sep="|"):
    return s.split(sep)[0].strip() if s else ""


def departement(cp, dept_siege):
    cp = (cp or "").strip()
    if len(cp) == 5 and cp.isdigit():
        if cp.startswith("97") or cp.startswith("98"):
            return cp[:3]
        if cp.startswith("20"):
            return "2A" if cp < "20200" else "2B"
        return cp[:2]
    return (dept_siege or "").strip()


LOCAUX_FACTICES = {"votre", "your", "email", "e-mail", "mail", "exemple", "example", "test", "nom", "prenom", "name",
                   "user", "utilisateur", "adresse", "monadresse", "xxx", "abc", "jean.dupont", "marie.dupont", "john.doe"}


def email_apparente(email, lead, site_dom):
    """L'e-mail appartient-il à l'entreprise ? Même domaine que le site, webmail (TPE), ou domaine qui porte
    un mot distinctif du nom. Sinon c'est un tiers présent sur la page (hébergeur, agence web, assureur…)."""
    dom = domaine_email(email)
    if not dom:
        return False
    if dom == site_dom or site_dom.endswith("." + dom) or dom.endswith("." + site_dom):
        return True
    if dom in WEBMAILS:
        return True
    dom_sans_tld = dom.rsplit(".", 1)[0]
    dom_compact = re.sub(r"[^a-z0-9]", "", dom_sans_tld)
    for t in tokens_nom(lead.get("nom", ""), lead.get("enseigne", "")):
        if len(t) >= 4 and t not in LOCAUX_GENERIQUES and t in dom_compact:
            return True
    # sigle : « Groupe Roy Energie » → gre-enr.fr ; « La Charpente Courvilloise » → lccrouvet.fr
    segments = [s for s in re.split(r"[^a-z0-9]+", dom_sans_tld) if s]
    for texte in (lead.get("nom", ""), lead.get("enseigne", "")):
        for morceau in re.split(r"[()|,]", norm(texte)):
            mots = [m for m in re.split(r"[^a-z0-9]+", morceau) if m]
            sigle = "".join(m[0] for m in mots)
            if len(sigle) >= 3 and (dom_compact.startswith(sigle) or sigle in segments):
                return True
    return False


def choisir_email(emails, lead, site_dom):
    """Classe les e-mails candidats : même domaine que le site > générique > nominatif > webmail ;
    écarte les adresses personnelles, factices et celles de tiers."""
    classes = []
    ecartes = []
    for e in emails:
        e = e.strip().lower()
        if not e or "@" not in e:
            continue
        local = e.split("@", 1)[0]
        if local in LOCAUX_FACTICES or domaine_email(e) in PLACEHOLDER_DOMAINES:
            ecartes.append(e + "(factice)")
            continue
        if not email_apparente(e, lead, site_dom):
            ecartes.append(e + "(tiers)")
            continue
        t, personnel = typer_email(e, lead)
        if personnel:
            ecartes.append(e + "(personnel)")
            continue
        rang = {"generique": 1, "nominatif": 2, "webmail": 3}[t]
        if domaine_email(e) == site_dom:
            rang -= 1
        classes.append((rang, e, t))
    classes.sort()
    return classes, ecartes


def main(argv):
    args = [a for a in argv[1:]]
    if not args or "-h" in args or "--help" in args:
        print(__doc__)
        return 0
    out, data_dir, rejets, ajouter, entrees, config = None, None, None, False, [], None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--out":
            out = args[i + 1]; i += 2
        elif a == "--data-dir":
            data_dir = args[i + 1]; i += 2
        elif a == "--rejets":
            rejets = args[i + 1]; i += 2
        elif a == "--ajouter":
            ajouter = True; i += 1
        elif a == "--config":
            config = args[i + 1]; i += 2
        else:
            entrees.append(a); i += 1
    data_dir = os.path.abspath(data_dir or os.path.join(PIPELINE, "data"))
    out = os.path.abspath(out or os.path.join(data_dir, "queue.csv"))
    rejets = os.path.abspath(rejets or os.path.join(data_dir, "queue_rejets.csv"))
    os.makedirs(data_dir, exist_ok=True)
    cible = charger_cible_tpe(os.path.abspath(config) if config else os.path.join(PIPELINE, "config.json"))

    with open(os.path.join(ICI, "naf_libelles.json"), encoding="utf-8") as f:
        libelles = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

    excl = ensembles_exclusion(data_dir)
    aujourd_hui = date.today().isoformat()

    lignes = []
    for ch in entrees:
        if not os.path.exists(ch) or os.path.getsize(ch) == 0:
            print(f"  (ignoré : {ch} absent ou vide)", file=sys.stderr)
            continue
        with open(ch, encoding="utf-8-sig", newline="") as f:
            lignes.extend(csv.DictReader(f, delimiter=";"))

    stats = {
        "entree": {"lignes": len(lignes), "sites": {"haute": 0, "moyenne": 0, "basse": 0, "aucun": 0}, "avec_email": 0},
        "exclusions": {"hors_cible_taille": 0, "sans_site": 0, "site_annuaire": 0, "confiance_basse": 0, "sans_email": 0, "email_personnel_tiers_ou_factice": 0,
                       "opposition_ou_ledger": 0, "doublon_domaine": 0},
        "email_type": {"generique": 0, "nominatif": 0, "webmail": 0},
    }
    rejets_rows = []
    candidats = {}

    def rejeter(lead, motif):
        rejets_rows.append({
            "date": aujourd_hui, "siren": lead.get("siren", ""), "nom": lead.get("nom", ""),
            "ville": lead.get("etab_zone_ville") or lead.get("ville", ""), "site": lead.get("site_web", ""),
            "site_confiance": lead.get("site_confiance", ""), "email": lead.get("emails_publics", ""), "motif": motif,
        })

    for lead in lignes:
        site = (lead.get("site_web") or lead.get("site") or "").strip()
        conf = (lead.get("site_confiance") or "").strip().lower()
        emails_bruts = [e for e in (lead.get("emails_publics") or lead.get("email") or "").split("|") if e.strip()]
        stats["entree"]["sites"][conf if conf in ("haute", "moyenne", "basse") else "aucun"] += 1
        if emails_bruts:
            stats["entree"]["avec_email"] += 1
        detail_taille = hors_cible_taille(lead, cible)
        if detail_taille:
            stats["exclusions"]["hors_cible_taille"] += 1; rejeter(lead, f"hors_cible_taille:{detail_taille}"); continue
        if not site:
            stats["exclusions"]["sans_site"] += 1; rejeter(lead, "sans_site"); continue
        site_dom = domaine_site(site)
        if not site_dom or est_annuaire(site_dom):
            stats["exclusions"]["site_annuaire"] += 1; rejeter(lead, f"site_annuaire:{site_dom}"); continue
        if conf not in ("haute", "moyenne"):
            stats["exclusions"]["confiance_basse"] += 1; rejeter(lead, f"site_confiance={conf or 'vide'}"); continue
        emails_bruts = [e for e in emails_bruts if domaine_email(e.strip().lower()) not in PLACEHOLDER_DOMAINES
                        and not est_annuaire(domaine_email(e.strip().lower()))]
        if not emails_bruts:
            stats["exclusions"]["sans_email"] += 1; rejeter(lead, "sans_email"); continue
        classes, ecartes = choisir_email(emails_bruts, lead, site_dom)
        if not classes:
            stats["exclusions"]["email_personnel_tiers_ou_factice"] += 1
            rejeter(lead, "emails_ecartes:" + ",".join(ecartes)); continue
        _, email, email_type = classes[0]
        siren = (lead.get("siren") or "").strip()
        if site_dom in excl["domaines"] or email in excl["emails"] or siren in excl["sirens"] \
                or (domaine_email(email) not in WEBMAILS and domaine_email(email) in excl["domaines"]):
            stats["exclusions"]["opposition_ou_ledger"] += 1; rejeter(lead, "opposition_ou_ledger"); continue
        try:
            score = int(float(lead.get("score_lead") or 0))
        except ValueError:
            score = 0
        cp = (lead.get("etab_zone_cp") or lead.get("code_postal") or "").strip()
        naf = (lead.get("naf") or "").strip()
        row = {
            "siren": siren,
            "nom": (lead.get("nom") or "").strip(),
            "enseigne": (lead.get("enseigne") or "").strip(),
            "naf": naf,
            "libelle_naf": libelles.get(naf, ""),
            "adresse": (lead.get("etab_zone_adresse") or lead.get("adresse") or "").strip(),
            "cp": cp,
            "ville": (lead.get("etab_zone_ville") or lead.get("ville") or "").strip(),
            "dept": departement(cp, lead.get("departement")),
            "dirigeants": (lead.get("dirigeants") or "").strip(),
            "site": site,
            "site_confiance": conf,
            "email": email,
            "email_type": email_type,
            "tel": premier(lead.get("telephones_publics") or lead.get("tel") or ""),
            "score_lead": score,
            "date_collecte": (lead.get("date_collecte") or aujourd_hui).strip(),
        }
        # dédoublonnage par domaine : on garde le meilleur score, puis la meilleure confiance
        cle = site_dom
        rang = (score, 1 if conf == "haute" else 0)
        if cle in candidats:
            stats["exclusions"]["doublon_domaine"] += 1
            if rang <= candidats[cle][0]:
                rejeter(lead, "doublon_domaine"); continue
            rejeter(candidats[cle][1], "doublon_domaine")
        candidats[cle] = (rang, row)

    nouvelles = [r for _, r in candidats.values()]

    # fusion éventuelle avec la file existante
    existantes = []
    if ajouter and os.path.exists(out) and os.path.getsize(out) > 0:
        with open(out, encoding="utf-8-sig", newline="") as f:
            existantes = list(csv.DictReader(f, delimiter=";"))
        doms = {domaine_site(r.get("site", "")) for r in existantes}
        avant = len(nouvelles)
        nouvelles = [r for r in nouvelles if domaine_site(r["site"]) not in doms]
        stats["exclusions"]["doublon_domaine"] += avant - len(nouvelles)
    finales = existantes + nouvelles
    finales.sort(key=lambda r: -int(r.get("score_lead") or 0))
    for r in nouvelles:
        stats["email_type"][r["email_type"]] += 1

    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES_QUEUE, delimiter=";", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in finales:
            w.writerow({c: r.get(c, "") for c in COLONNES_QUEUE})
    with open(rejets, "a" if ajouter else "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES_REJETS, delimiter=";", lineterminator="\n")
        if f.tell() == 0 or not ajouter:
            w.writeheader()
        w.writerows(rejets_rows)

    stats["listes"] = {"opposition": excl["n_opposition"], "ledger": excl["n_ledger"]}
    stats["cible_tpe"] = cible
    stats["sortie"] = {"fichier": out, "nouvelles": len(nouvelles), "total_file": len(finales), "rejets": rejets}
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
