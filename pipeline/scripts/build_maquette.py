#!/home/user/.venv-webtest/bin/python
"""build_maquette.py — génère la maquette de page d'accueil d'un prospect (Clients Ici).

Usage :
  build_maquette.py --spec spec.json --out <dossier>/index.html [--audit audit.json]
                    [--template templates/maquette.html] [--agence "Clients Ici"]

Le spec ne contient QUE des informations confirmées, lues sur le site du prospect :
  nom (obligatoire), metier, ville, zone, tel, email, adresse,
  services  : liste de chaînes ou d'objets {titre, detail}
  horaires  : liste de chaînes ("Lundi–vendredi : 8 h – 18 h") ou d'objets {jours, heures}
  slogan    : phrase du site (facultatif)
  preuves_verifiees : liste de chaînes (ex. « SIRET affiché »), uniquement si lues sur le site
  palette   : batiment | commerce | service
  objectif  : devis | appel | contact
  metier_court (facultatif) : libellé court pour le titre si `metier` est un libellé NAF long
  domaine_source (facultatif) : domaine du site d'origine (sinon pris dans l'audit)

--audit : audit.json produit par audit_site.py ; sert seulement à lister les constats haute/moyenne
          dans un volet repliable du bandeau et à nommer le domaine source. Aucune donnée inventée.

Les sections sans donnée confirmée sont omises. Sortie : index.html + une ligne JSON sur stdout.
Code retour : 0 si écrit, 2 si arguments/spec invalides.
"""
import argparse
import html
import json
import os
import re
import sys
import tempfile
from datetime import date

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
TEMPLATE_DEFAUT = os.path.join(PIPELINE, "templates", "maquette.html")

PALETTES = ("batiment", "commerce", "service")
OBJECTIFS = ("devis", "appel", "contact")

# ----------------------------------------------------------------------------
# Mini-moteur de gabarit : {{var}}, {{{var}}} (brut), {{#if clé}}…{{/if}}, {{#each clé}}…{{/each}}, {{.}}
# ----------------------------------------------------------------------------
_TOKEN = re.compile(r"\{\{\{\s*([\w.]+)\s*\}\}\}|\{\{\s*(#if|#each|/if|/each)?\s*([\w.]*)\s*\}\}")


def _parse(src):
    """Transforme le gabarit en arbre : liste de ('text', s) | ('var', nom, brut) | ('if', nom, enfants) | ('each', nom, enfants)."""
    pile = [[]]
    attend = []
    pos = 0
    for m in _TOKEN.finditer(src):
        if m.start() > pos:
            pile[-1].append(("text", src[pos:m.start()]))
        pos = m.end()
        if m.group(1):
            pile[-1].append(("var", m.group(1), True))
            continue
        tag, nom = m.group(2), m.group(3)
        if tag in ("#if", "#each"):
            pile.append([])
            attend.append((tag[1:], nom))
        elif tag in ("/if", "/each"):
            if not attend or attend[-1][0] != tag[1:]:
                raise ValueError(f"gabarit : fermeture {tag} inattendue (position {m.start()})")
            genre, nom_ouvert = attend.pop()
            enfants = pile.pop()
            pile[-1].append((genre, nom_ouvert, enfants))
        else:
            pile[-1].append(("var", nom or ".", False))
    if attend:
        raise ValueError(f"gabarit : bloc non fermé {attend[-1]}")
    if pos < len(src):
        pile[-1].append(("text", src[pos:]))
    return pile[0]


def _lookup(ctx_pile, nom):
    if nom == ".":
        return ctx_pile[-1]
    for ctx in reversed(ctx_pile):
        if isinstance(ctx, dict) and nom in ctx:
            return ctx[nom]
    return None


def _vrai(v):
    if v is None or v is False:
        return False
    if isinstance(v, (list, dict, str)):
        return len(v) > 0
    return True


def _render(noeuds, ctx_pile, out):
    for n in noeuds:
        genre = n[0]
        if genre == "text":
            out.append(n[1])
        elif genre == "var":
            v = _lookup(ctx_pile, n[1])
            if v is None or v is False:
                continue
            s = str(v)
            out.append(s if n[2] else html.escape(s, quote=True))
        elif genre == "if":
            if _vrai(_lookup(ctx_pile, n[1])):
                _render(n[2], ctx_pile, out)
        elif genre == "each":
            v = _lookup(ctx_pile, n[1])
            if isinstance(v, list):
                for item in v:
                    _render(n[2], ctx_pile + [item], out)


def rendre(gabarit, ctx):
    out = []
    _render(_parse(gabarit), [ctx], out)
    return "".join(out)


# ----------------------------------------------------------------------------
# Préparation des données
# ----------------------------------------------------------------------------
def _txt(v, maxi=400):
    """Chaîne nettoyée (espaces, longueur), ou None si vide."""
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    return s[:maxi] if s else None


def _liste(v):
    return v if isinstance(v, list) else ([] if v in (None, "") else [v])


def normaliser_services(brut):
    res = []
    for s in _liste(brut)[:12]:
        if isinstance(s, dict):
            t = _txt(s.get("titre") or s.get("nom") or s.get("titre_court"), 120)
            d = _txt(s.get("detail") or s.get("description"), 240)
        else:
            t, d = _txt(s, 120), None
        if t:
            res.append({"titre": t, "detail": d})
    return res


def normaliser_horaires(brut):
    res = []
    for h in _liste(brut)[:10]:
        if isinstance(h, dict):
            j, hh = _txt(h.get("jours"), 80), _txt(h.get("heures"), 80)
        else:
            s = _txt(h, 160) or ""
            if ":" in s:
                j, hh = (x.strip() for x in s.split(":", 1))
            else:
                j, hh = s, ""
        if j:
            res.append({"jours": j, "heures": hh or ""})
    return res


def domaine_de(url):
    if not url:
        return None
    m = re.match(r"^(?:https?://)?([^/:?#]+)", str(url).strip(), re.I)
    if not m:
        return None
    return m.group(1).lower().removeprefix("www.")


def lire_audit(chemin):
    """Renvoie (points haute/moyenne, domaine) ; tolère un fichier absent ou mal formé (avertit)."""
    if not chemin:
        return [], None, None
    try:
        with open(chemin, encoding="utf-8") as f:
            a = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [], None, f"audit illisible : {e}"
    points = []
    constats = ((a.get("analyse") or {}).get("constats") or [])
    for c in constats:
        if not isinstance(c, dict):
            continue
        if c.get("gravite") in ("haute", "moyenne"):
            t = _txt(c.get("titre"), 160)
            if t:
                points.append(t)
    url = ((a.get("cible") or {}).get("url_finale") or (a.get("cible") or {}).get("url_demandee")
           or ((a.get("meta") or {}).get("parametres") or {}).get("url"))
    return points[:6], domaine_de(url), None


def verifier_titre(titre, valeurs):
    """Garde-fou : le titre (H1, <title>) ne doit affirmer que ce que le spec contient.
    Il est composé de métier/métier court, nom et ville ; sans ville dans le spec, il ne contient aucun « à <lieu> »."""
    admis = {valeurs.get("nom")}
    for m in (valeurs.get("metier_court"), valeurs.get("metier")):
        if m:
            admis.add(m)
            if valeurs.get("ville"):
                admis.add(f"{m} à {valeurs['ville']}")
    if titre not in admis:
        raise ValueError(f"titre « {titre} » non déductible du spec (admis : {sorted(a for a in admis if a)})")
    if not valeurs.get("ville") and re.search(r"\bà\s+\S", titre) and titre not in (valeurs.get("metier_court"), valeurs.get("metier"), valeurs.get("nom")):
        raise ValueError(f"titre « {titre} » affirme un lieu absent du spec")
    return titre


def construire_contexte(spec, audit_points, domaine_audit, agence):
    nom = _txt(spec.get("nom"), 120)
    if not nom:
        raise ValueError("spec : le champ « nom » est obligatoire")
    palette = (spec.get("palette") or "batiment").strip().lower()
    if palette not in PALETTES:
        raise ValueError(f"spec : palette inconnue « {palette} » (attendu : {', '.join(PALETTES)})")
    objectif = (spec.get("objectif") or "contact").strip().lower()
    if objectif not in OBJECTIFS:
        raise ValueError(f"spec : objectif inconnu « {objectif} » (attendu : {', '.join(OBJECTIFS)})")

    metier = _txt(spec.get("metier"), 160)
    metier_court = _txt(spec.get("metier_court"), 80) or metier
    ville = _txt(spec.get("ville"), 80)
    zone = _txt(spec.get("zone"), 400)
    tel = _txt(spec.get("tel"), 40)
    email = _txt(spec.get("email"), 120)
    adresse = _txt(spec.get("adresse"), 200)
    slogan = _txt(spec.get("slogan"), 200)
    services = normaliser_services(spec.get("services"))
    horaires = normaliser_horaires(spec.get("horaires"))
    preuves = [p for p in (_txt(x, 160) for x in _liste(spec.get("preuves_verifiees") or spec.get("preuves"))) if p][:8]

    # Titre principal (H1 et <title>) : uniquement des valeurs du spec. « {metier_court} à {ville} » seulement si la
    # ville est dans le spec (la zone peut manquer : la ville suffit) ; sans ville, aucune localisation n'est affirmée.
    if metier_court and ville:
        titre_hero = f"{metier_court} à {ville}"
    elif metier_court:
        titre_hero = metier_court
    else:
        titre_hero = nom
    verifier_titre(titre_hero, {"metier_court": metier_court, "metier": metier, "ville": ville, "nom": nom, "zone": zone})

    # Accroche : slogan du site s'il existe ; sinon une reformulation des seules données confirmées.
    if slogan:
        accroche = slogan
    else:
        morceaux = [nom]
        if metier:
            morceaux.append(metier.lower() if metier[:1].isupper() and not metier.isupper() else metier)
        phrase = ", ".join(morceaux) if len(morceaux) > 1 else nom
        if ville:
            phrase += f", à {ville}"
        accroche = phrase + "."

    cta = {"devis": "Demander un devis", "appel": "Nous joindre", "contact": "Nous contacter"}[objectif]
    contact_titre = {"devis": "Demander un devis", "appel": "Nous joindre", "contact": "Nous contacter"}[objectif]
    bouton = {"devis": "Envoyer ma demande de devis", "appel": "Demander à être rappelé", "contact": "Envoyer le message"}[objectif]
    champ_message_lib = {"devis": "Les travaux ou la prestation souhaités", "appel": "Le motif de votre appel",
                         "contact": "Votre message"}[objectif]

    if tel:
        title_tel = ("Numéro affiché à titre d'aperçu : volontairement non cliquable dans cette maquette, "
                     "pour ne provoquer aucun appel réel.")
    else:
        title_tel = None
    title_email = ("Adresse affichée à titre d'aperçu : volontairement non cliquable dans cette maquette, "
                   "pour n'envoyer aucun e-mail réel.") if email else None

    description = f"{titre_hero}. {nom}"
    if adresse:
        description += f", {adresse}"
    description += ". Maquette de discussion, non officielle."

    horaires_resume = None
    if horaires and len(horaires) <= 2:
        horaires_resume = " ; ".join(f"{h['jours']} {h['heures']}".strip() for h in horaires)

    domaine_source = _txt(spec.get("domaine_source"), 120) or domaine_audit

    return {
        "palette": palette, "objectif": objectif, "agence": agence, "date": date.today().strftime("%d/%m/%Y"),
        "nom": nom, "metier": metier, "ville": ville, "zone": zone, "tel": tel, "email": email, "adresse": adresse,
        "services": services, "services_classe": "trois" if len(services) >= 6 else "",
        "horaires": horaires, "horaires_resume": horaires_resume if len(horaires) > 2 else None,
        "preuves": preuves, "slogan": slogan,
        "titre_hero": titre_hero, "accroche": accroche,
        "titre_page": f"{titre_hero} | {nom} (maquette)"[:120],
        "description_page": description[:220],
        "cta_label": cta, "contact_titre": contact_titre, "bouton_label": bouton,
        "champ_message_lib": champ_message_lib,
        "champ_tel": objectif in ("appel", "devis"), "champ_email": objectif in ("contact", "devis"),
        "title_tel": title_tel, "title_email": title_email,
        "audit_points": audit_points, "domaine_source": domaine_source,
    }


def ecrire_atomique(chemin, contenu):
    dossier = os.path.dirname(os.path.abspath(chemin)) or "."
    os.makedirs(dossier, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".maquette-", suffix=".tmp", dir=dossier)
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


def verifier_sortie(html_out):
    """Garde-fous : aucun lien tel:/mailto:, aucune ressource externe, noindex présent."""
    problemes = []
    if re.search(r'href\s*=\s*["\'](tel|mailto):', html_out, re.I):
        problemes.append("lien tel:/mailto: présent")
    if re.search(r'(src|href)\s*=\s*["\']https?://', html_out, re.I):
        problemes.append("ressource externe présente")
    if 'content="noindex, nofollow"' not in html_out:
        problemes.append("meta robots noindex absente")
    if "Proposition non officielle" not in html_out:
        problemes.append("bandeau d'avertissement absent")
    return problemes


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spec", required=True, help="spec.json (informations confirmées du prospect)")
    p.add_argument("--out", required=True, help="chemin du index.html à écrire")
    p.add_argument("--audit", help="audit.json (audit_site.py), facultatif")
    p.add_argument("--template", default=TEMPLATE_DEFAUT, help="gabarit HTML (défaut : templates/maquette.html)")
    p.add_argument("--agence", default="Clients Ici", help="nom de l'agence affiché dans le bandeau et le pied de page")
    args = p.parse_args(argv)

    avertissements = []
    try:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)
        if not isinstance(spec, dict):
            raise ValueError("spec : un objet JSON est attendu")
        with open(args.template, encoding="utf-8") as f:
            gabarit = f.read()
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(json.dumps({"ok": False, "erreur": str(e)}, ensure_ascii=False))
        return 2

    audit_points, domaine_audit, err_audit = lire_audit(args.audit)
    if err_audit:
        avertissements.append(err_audit)

    try:
        ctx = construire_contexte(spec, audit_points, domaine_audit, args.agence)
        html_out = rendre(gabarit, ctx)
    except ValueError as e:
        print(json.dumps({"ok": False, "erreur": str(e)}, ensure_ascii=False))
        return 2

    problemes = verifier_sortie(html_out)
    if problemes:
        print(json.dumps({"ok": False, "erreur": "sortie refusée : " + " ; ".join(problemes)}, ensure_ascii=False))
        return 2

    ecrire_atomique(args.out, html_out)
    sections = [s for s, v in (("prestations", ctx["services"]), ("zone", ctx["zone"]), ("garanties", ctx["preuves"]),
                               ("horaires", ctx["horaires"])) if v]
    print(json.dumps({
        "ok": True, "out": os.path.abspath(args.out), "octets": len(html_out.encode("utf-8")),
        "palette": ctx["palette"], "objectif": ctx["objectif"], "titre": ctx["titre_hero"],
        "sections": ["accueil"] + sections + ["contact"], "constats_audit_affiches": len(audit_points),
        "avertissements": avertissements,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
