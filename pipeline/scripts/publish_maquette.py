#!/home/user/.venv-webtest/bin/python
"""publish_maquette.py — prépare la publication d'une maquette sous un lien privé (sans rien publier).

Usage :
  publish_maquette.py --maquette <dossier>/index.html [--site-dir <racine>/site] [--base-url https://clientsici.fr]
                      [--htaccess deploy/apercu.htaccess] [--jeton XXXX] [--supprimer <jeton>]

Copie la maquette dans <site-dir>/apercu/<jeton>/index.html avec le .htaccess d'aperçu (noindex, pas de
listage) et affiche l'URL future https://clientsici.fr/apercu/<jeton>/ . Le jeton fait 20 caractères
aléatoires [a-z0-9] (secrets). La mise en ligne réelle se fait par le dépôt (commit + push sur main →
GitHub Action deploy/.github-workflows-deploy.yml) : ce script n'ouvre aucune connexion.
--supprimer <jeton> : retire le dossier d'aperçu (à committer ensuite pour le retirer de l'hébergement).
Sortie JSON : {jeton, chemin, url, htaccess, publie: false}. Codes : 0 ok, 1 refus, 2 arguments invalides.
"""
import argparse
import json
import os
import re
import secrets
import shutil
import string
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
RACINE = os.path.dirname(PIPELINE)
SITE_DEFAUT = os.path.join(RACINE, "site")
HTACCESS_DEFAUT = os.path.join(PIPELINE, "deploy", "apercu.htaccess")
ALPHABET = string.ascii_lowercase + string.digits


def jeton_aleatoire(n=20):
    return "".join(secrets.choice(ALPHABET) for _ in range(n))


def copier_atomique(src, dst):
    dossier = os.path.dirname(dst)
    fd, tmp = tempfile.mkstemp(prefix=".pub-", dir=dossier)
    os.close(fd)
    try:
        shutil.copyfile(src, tmp)
        os.chmod(tmp, 0o644)
        os.replace(tmp, dst)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--maquette", help="index.html produit par build_maquette.py")
    p.add_argument("--site-dir", default=SITE_DEFAUT, help=f"dossier site/ du dépôt (défaut : {SITE_DEFAUT})")
    p.add_argument("--base-url", default="https://clientsici.fr")
    p.add_argument("--htaccess", default=HTACCESS_DEFAUT)
    p.add_argument("--jeton", help="jeton imposé (20 caractères [a-z0-9]) ; sinon tiré au hasard")
    p.add_argument("--supprimer", metavar="JETON", help="retire site/apercu/<jeton>/ au lieu de publier")
    a = p.parse_args(argv)

    base = a.base_url.rstrip("/")
    if not re.match(r"^https://[a-z0-9.-]+$", base):
        print(json.dumps({"ok": False, "erreur": "--base-url doit être https://<hôte>"}, ensure_ascii=False)); return 2
    apercu_dir = os.path.join(os.path.abspath(a.site_dir), "apercu")

    if a.supprimer:
        if not re.fullmatch(r"[a-z0-9]{20}", a.supprimer):
            print(json.dumps({"ok": False, "erreur": "jeton invalide"}, ensure_ascii=False)); return 2
        cible = os.path.join(apercu_dir, a.supprimer)
        if not os.path.isdir(cible):
            print(json.dumps({"ok": False, "erreur": "aperçu introuvable", "chemin": cible}, ensure_ascii=False)); return 1
        shutil.rmtree(cible)
        print(json.dumps({"ok": True, "action": "supprime", "chemin": cible, "url": f"{base}/apercu/{a.supprimer}/",
                          "a_faire": "committer et pousser pour retirer l'aperçu de l'hébergement"}, ensure_ascii=False))
        return 0

    if not a.maquette:
        print(json.dumps({"ok": False, "erreur": "--maquette requis"}, ensure_ascii=False)); return 2
    if not os.path.isfile(a.maquette):
        print(json.dumps({"ok": False, "erreur": f"maquette introuvable : {a.maquette}"}, ensure_ascii=False)); return 2
    if not os.path.isfile(a.htaccess):
        print(json.dumps({"ok": False, "erreur": f".htaccess d'aperçu introuvable : {a.htaccess}"}, ensure_ascii=False)); return 2
    try:
        with open(a.maquette, encoding="utf-8") as f:
            contenu = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(json.dumps({"ok": False, "erreur": f"maquette illisible : {e}"}, ensure_ascii=False)); return 2
    # garde-fous : même règles que build_maquette.py
    refus = []
    if 'content="noindex, nofollow"' not in contenu: refus.append("meta noindex absente")
    if "Proposition non officielle" not in contenu: refus.append("bandeau d'avertissement absent")
    if re.search(r'href\s*=\s*["\'](tel|mailto):', contenu, re.I): refus.append("lien tel:/mailto: présent")
    if re.search(r'(src|href)\s*=\s*["\']https?://', contenu, re.I): refus.append("ressource externe présente")
    if refus:
        print(json.dumps({"ok": False, "erreur": "maquette refusée : " + " ; ".join(refus)}, ensure_ascii=False)); return 1

    jeton = a.jeton or jeton_aleatoire()
    if not re.fullmatch(r"[a-z0-9]{20}", jeton):
        print(json.dumps({"ok": False, "erreur": "jeton invalide (20 caractères [a-z0-9])"}, ensure_ascii=False)); return 2
    dossier = os.path.join(apercu_dir, jeton)
    if os.path.exists(dossier) and not a.jeton:
        jeton = jeton_aleatoire(); dossier = os.path.join(apercu_dir, jeton)
    os.makedirs(dossier, exist_ok=True)
    copier_atomique(a.maquette, os.path.join(dossier, "index.html"))
    copier_atomique(a.htaccess, os.path.join(dossier, ".htaccess"))
    # .htaccess racine d'apercu/ : pas de listage des jetons même si un dossier parent le permettait
    racine_ht = os.path.join(apercu_dir, ".htaccess")
    if not os.path.exists(racine_ht):
        with open(racine_ht, "w", encoding="utf-8") as f:
            f.write("Options -Indexes\n<IfModule mod_headers.c>\n  Header set X-Robots-Tag \"noindex, nofollow, noarchive\"\n</IfModule>\n")
    print(json.dumps({"ok": True, "publie": False, "jeton": jeton, "chemin": os.path.join(dossier, "index.html"),
                      "htaccess": os.path.join(dossier, ".htaccess"), "url": f"{base}/apercu/{jeton}/",
                      "a_faire": "git add site/apercu && git commit && git push (main) ; l'Action FTP met en ligne"},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
