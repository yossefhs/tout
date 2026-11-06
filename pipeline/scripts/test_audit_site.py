#!/home/user/.venv-webtest/bin/python
# -*- coding: utf-8 -*-
"""
test_audit_site.py — Tests hors ligne d'audit_site.py (aucune requête réseau).

    /home/user/.venv-webtest/bin/python scripts/test_audit_site.py          # tous les tests
    ... -k contact                                                           # filtre unittest

Couvre : regex téléphone (dates ignorées), titres multi-lignes et hors formulaire, listes de prestations,
services_listes (filtres, plafond 12, pages recrutement/actualités exclues), choix des pages internes
(recrutement jamais « services »), correspondance_entreprise, domaine_final, textes de correction (alt selon
--metier, « ressources en erreur (4xx) »), et les trois cas du bouton de contact à 375 px — dont un test
Playwright sur une page locale (file://) avec un bouton fixe, sauté si le navigateur est indisponible.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_site as A  # noqa: E402

PW_BROWSERS = "/home/user/.venv-webtest/ms-playwright"


def page_from_html(html: str, url: str = "https://exemple.test/", role: str = "accueil") -> dict:
    res = {"final_url": url, "status": 200, "content_type": "text/html; charset=utf-8",
           "body_bytes": html.encode("utf-8"), "encodage_declare": "utf-8"}
    return A.analyse_page(url, res, role)


def base_audit(pages: list[dict], appels: list[dict] | None = None, mm: bool = True) -> dict:
    """Audit minimal au schéma attendu par analyse(), avec un navigateur mobile factice."""
    nav = {"date": "2026-11-05T10:00:00+00:00", "vues": {}}
    if mm:
        nav["vues"]["mobile"] = {"metriques": {"innerWidth": 375, "scrollWidth": 375, "debordement": False,
                                               "appels": appels or [], "plus_petit_texte_px": 16, "textes_moins_12px": 0},
                                 "erreurs_console_nombre": 0, "octets_transferes": 100_000, "requetes": 10}
    return {"cible": {"url_demandee": pages[0]["url"], "url_finale": pages[0]["url"], "status": 200},
            "http": {"hsts": None, "test_http": {"url": "http://exemple.test/", "status": 301, "final_url": pages[0]["url"]},
                     "test_https": None, "test_www": None},
            "pages": pages, "robots": {"existe": False}, "sitemap": {"existe": False},
            "navigateur": nav, "lighthouse": {"statut": "non mesuré", "raison": "test"}}


HOME = """<!doctype html><html lang="fr"><head><title>Plomberie Dupont Chartres</title>
<meta name="viewport" content="width=device-width"><meta name="description" content="Plombier à Chartres"></head>
<body><header><nav><a href="/contact/">Contact</a><a href="/nos-prestations/">Prestations</a>
<a href="/recrutement/">Nos offres d'emploi</a><a href="/actualites/">Actualités</a></nav></header>
<h1>Plombier chauffagiste à Chartres</h1>
<h2>Nos prestations</h2>
<ul><li>Dépannage plomberie</li><li>Installation de chaudière</li><li>Débouchage de canalisations</li></ul>
<h2>Ensemble,<br>construisons votre projet</h2>
<h2>Pourquoi nous choisir ?</h2>
<h3>Salle de bain clé en main</h3>
<form action="/contact"><h2>Vos coordonnées</h2><h3>Informations sur votre projet</h3></form>
<p>SARL DUPONT PLOMBERIE, 12 rue des Lilas 28000 Chartres. SIRET 123 456 789 00012. Dernière mise à jour 2026-09-15 15:35:05.</p>
<p>Tél. <a href="tel:0237000000">02 37 00 00 00</a></p>
<footer>© 2026 Dupont</footer></body></html>"""

RECRUT = """<!doctype html><html lang="fr"><head><title>Recrutement | Dupont</title></head><body>
<h2>Nos offres d'emploi</h2><h3>Plombier H/F</h3><h3>Chauffagiste H/F</h3></body></html>"""


class TestTelephones(unittest.TestCase):
    def test_date_non_lue_comme_numero(self):
        self.assertEqual([m.group(0) for m in A.PHONE_RE.finditer("2026-09-15 15:35:05 2026-09-15 15:45:11")], [])

    def test_formats_courants(self):
        for t, attendu in [("Tél. 02 38 46 15 67", "02 38 46 15 67"), ("tel:0238801801", "0238801801"),
                           ("+33 6 12 34 56 78", "+33 6 12 34 56 78"), ("06.12.34.56.78", "06.12.34.56.78"),
                           ("Tél:0612345678", "0612345678"), ("02-38-46-15-67", "02-38-46-15-67")]:
            self.assertEqual([m.group(0) for m in A.PHONE_RE.finditer(t)], [attendu], t)

    def test_separateurs_melanges_refuses(self):
        self.assertEqual([m.group(0) for m in A.PHONE_RE.finditer("05 2026-09-15")], [])

    def test_page_telephones(self):
        p = page_from_html(HOME)
        self.assertEqual(p["telephones_detectes"], ["02 37 00 00 00"])


class TestTitresEtServices(unittest.TestCase):
    def test_titre_multiligne_joint(self):
        p = page_from_html(HOME)
        self.assertIn("Ensemble, construisons votre projet", p["h2"])

    def test_titres_hors_formulaire(self):
        p = page_from_html(HOME)
        self.assertNotIn("Vos coordonnées", p["_titres_hors_formulaire"])
        self.assertNotIn("Informations sur votre projet", p["_titres_hors_formulaire"])
        self.assertIn("Vos coordonnées", p["h2"])  # la sortie h2 brute reste complète

    def test_liste_prestations(self):
        p = page_from_html(HOME)
        self.assertEqual(p["_listes_prestations"][0]["elements"],
                         ["Dépannage plomberie", "Installation de chaudière", "Débouchage de canalisations"])

    def test_services_listes_filtres(self):
        home = page_from_html(HOME)
        rec = page_from_html(RECRUT, "https://exemple.test/recrutement/", "services")
        s = A.services_listes([home, rec])
        self.assertEqual(s[:3], ["Dépannage plomberie", "Installation de chaudière", "Débouchage de canalisations"])
        self.assertIn("Salle de bain clé en main", s)
        for interdit in ("Vos coordonnées", "Informations sur votre projet", "Pourquoi nous choisir ?", "Ensemble,",
                         "Nos prestations", "Plombier H/F", "Nos offres d'emploi"):
            self.assertNotIn(interdit, s, interdit)

    def test_clean_service_title(self):
        self.assertIsNone(A.clean_service_title("Ensemble,"))
        self.assertIsNone(A.clean_service_title("Comment ça marche ?"))
        self.assertIsNone(A.clean_service_title("NOS SOLUTIONS"))
        self.assertIsNone(A.clean_service_title("GROUPE ROY ÉNERGIE DÉMOCRATISE LE PHOTOVOLTAÏQUE"))
        self.assertIsNone(A.clean_service_title("Contactez notre agence : 02 38 46 15 67"))
        self.assertIsNone(A.clean_service_title("Demander une étude personnalisée"))
        self.assertEqual(A.clean_service_title("  Pose & Installation "), "Pose & Installation")

    def test_plafond_12_dedoublonne(self):
        lis = "".join(f"<li>Prestation {i}</li>" for i in range(1, 15)) + "<li>prestation 1</li>"
        html = f"<html><body><h2>Nos services</h2><ul>{lis}</ul><h3>Prestation 1</h3></body></html>"
        s = A.services_listes([page_from_html(html)])
        self.assertEqual(len(s), 12)
        self.assertEqual(len({A.norm_text(x) for x in s}), 12)

    def test_recrutement_jamais_services(self):
        home = page_from_html(HOME)
        chosen = A.choose_internal_pages(home, 4)
        cats = {c["url"].rstrip("/").rsplit("/", 1)[-1]: c["categorie"] for c in chosen}
        self.assertEqual(cats.get("nos-prestations"), "services")
        self.assertNotEqual(cats.get("recrutement"), "services")
        self.assertNotEqual(cats.get("actualites"), "services")


class TestCorrespondance(unittest.TestCase):
    def test_elements_retrouves(self):
        home = page_from_html(HOME)
        c = A.correspondance_entreprise([home], {"nom": "SARL DUPONT PLOMBERIE", "enseigne": "Plomberie Dupont",
                                                 "ville": "CHARTRES", "cp": "28000", "siren": "123456789"})
        self.assertEqual(c["elements_trouves"], ["nom", "enseigne", "ville", "cp", "siren"])
        self.assertEqual(c["details"]["nom"]["mode"], "libellé entier")

    def test_elements_absents(self):
        home = page_from_html(HOME)
        c = A.correspondance_entreprise([home], {"nom": "BOULANGERIE MARTIN", "ville": "Dreux", "cp": "28100", "siren": "987654321"})
        self.assertEqual(c["elements_trouves"], [])
        self.assertEqual(c["elements_non_trouves"], ["nom", "ville", "cp", "siren"])
        self.assertFalse(c["details"]["enseigne"]["fourni"])

    def test_accents_et_mots_significatifs(self):
        home = page_from_html(HOME)
        c = A.correspondance_entreprise([home], {"nom": "Société Dupont Plomberie Chartres"})
        self.assertEqual(c["elements_trouves"], ["nom"])
        self.assertTrue(c["details"]["nom"]["mode"].startswith("mots significatifs"))


class TestAnalyse(unittest.TestCase):
    def constat(self, an, debut):
        return next((c for c in an["constats"] if c["titre"].startswith(debut)), None)

    def test_tel_visible_sans_defiler(self):
        home = page_from_html(HOME)
        an = A.analyse(base_audit([home], [{"texte": "02 37 00 00 00", "href": "tel:0237000000", "tel": True, "dans_fold": True}]), {})
        self.assertIsNone(self.constat(an, "Aucun bouton de contact"))
        self.assertIsNone(self.constat(an, "Bouton de contact visible"))
        self.assertTrue(any(x.startswith("Bouton d'appel (tel:) visible") for x in an["ce_qui_fonctionne"]))

    def test_bouton_contact_sans_tel(self):
        home = page_from_html(HOME)
        appels = [{"texte": "", "href": "https://exemple.test/rendez-vous/", "tel": False, "dans_fold": True, "fixe": True,
                   "motif": "lien vers une page contact", "classes": "btn rdv"},
                  {"texte": "02 37 00 00 00", "href": "tel:0237000000", "tel": True, "dans_fold": False}]
        an = A.analyse(base_audit([home], appels), {})
        c = self.constat(an, "Bouton de contact visible sans défiler à 375 px, mais sans lien d'appel direct")
        self.assertIsNotNone(c)
        self.assertEqual(c["gravite"], "basse")
        self.assertNotIn("non visible", c["titre"] + c["preuve"]["valeur"])
        self.assertIn("fixe à l’écran", c["preuve"]["valeur"])
        self.assertIsNone(self.constat(an, "Aucun bouton de contact"))

    def test_aucun_bouton_contact(self):
        home = page_from_html(HOME)
        an = A.analyse(base_audit([home], [{"texte": "02 37 00 00 00", "href": "tel:0237000000", "tel": True, "dans_fold": False}]), {})
        c = self.constat(an, "Aucun bouton de contact visible sans défiler à 375 px")
        self.assertIsNotNone(c)
        self.assertEqual(c["gravite"], "moyenne")
        self.assertIsNone(self.constat(an, "Bouton de contact visible"))

    def test_sans_navigateur_aucun_constat_bouton(self):
        home = page_from_html(HOME)
        an = A.analyse(base_audit([home], mm=False), {})
        self.assertIsNone(self.constat(an, "Aucun bouton de contact"))
        self.assertIsNone(self.constat(an, "Bouton de contact visible"))

    def test_sans_tel_du_tout(self):
        html = HOME.replace('<a href="tel:0237000000">02 37 00 00 00</a>', "02 37 00 00 00")
        home = page_from_html(html)
        an = A.analyse(base_audit([home], []), {})
        c = self.constat(an, "Aucun numéro de téléphone cliquable")
        self.assertIsNotNone(c)
        self.assertIn("aucun bouton de contact visible sans défiler", c["preuve"]["valeur"])
        self.assertIsNone(self.constat(an, "Aucun bouton de contact"))   # pas de double constat moyen

    def test_textes_corrections(self):
        html = HOME.replace("<h1>", '<img src="a.jpg"><h1>')
        home = page_from_html(html)
        an = A.analyse(base_audit([home]), {"metier": "plombier chauffagiste", "ville": "Chartres"})
        c = self.constat(an, "Images sans attribut alt")
        self.assertIn("Plombier chauffagiste à Chartres", c["correction"])
        self.assertNotIn("carrelage", c["correction"])
        an2 = A.analyse(base_audit([home]), {})
        self.assertNotIn("ex.", self.constat(an2, "Images sans attribut alt")["correction"])
        audit = base_audit([home])
        audit["navigateur"]["vues"]["mobile"]["erreurs_console_nombre"] = 1
        audit["navigateur"]["vues"]["mobile"]["erreurs_console"] = ["Failed to load resource: 404"]
        c = self.constat(A.analyse(audit, {}), "Erreurs JavaScript")
        self.assertIn("ressources en erreur (4xx)", c["correction"])
        self.assertNotIn("fichiers manquants", c["correction"])

    def test_services_et_correspondance_dans_analyse(self):
        home = page_from_html(HOME)
        an = A.analyse(base_audit([home]), {"nom": "SARL DUPONT PLOMBERIE", "siren": "123456789"})
        self.assertEqual(an["correspondance_entreprise"]["elements_trouves"], ["nom", "siren"])
        self.assertIn("Dépannage plomberie", an["a_preserver"]["services_listes"])
        self.assertLessEqual(len(an["a_preserver"]["services_listes"]), 12)


class TestMainHorsLigne(unittest.TestCase):
    def test_domaine_final_et_resume(self):
        """URL injoignable (TLD .invalid) : audit.json écrit, domaine_demande rempli, domaine_final absent, résumé complet."""
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = A.main(["https://www.site-inexistant.invalid/", "--out", d, "--no-browser", "--no-lighthouse",
                               "--timeout", "3", "--nom", "Test", "--siren", "123456789"])
            self.assertEqual(code, 0)
            summary = json.loads(buf.getvalue().strip().splitlines()[-1])
            for k in ("url", "domaine_demande", "domaine_final", "verdict", "constats", "gravites", "lighthouse_performance",
                      "correspondance_entreprise", "duree_s", "out", "erreurs"):
                self.assertIn(k, summary)
            self.assertEqual(summary["domaine_demande"], "site-inexistant.invalid")
            self.assertIsNone(summary["domaine_final"])
            self.assertEqual(summary["correspondance_entreprise"], [])
            with open(os.path.join(d, "audit.json"), encoding="utf-8") as f:
                audit = json.load(f)
            self.assertEqual(audit["cible"]["domaine_demande"], "site-inexistant.invalid")
            self.assertIn("domaine_final", audit["cible"])
            self.assertEqual(audit["meta"]["parametres"]["siren"], "123456789")
            self.assertTrue(os.path.exists(os.path.join(d, "audit.md")))


FIXED_HTML = """<!doctype html><html lang="fr"><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{margin:0;font-family:sans-serif} .haut{height:1800px;background:#eee}
.rdv{position:fixed;right:16px;bottom:16px;width:56px;height:56px;border-radius:50%;background:#4a4;display:block}
.rdv span{position:absolute;left:-9999px} .tel{display:block;padding:12px}
nav a.menu{display:none}</style></head><body>
<nav><a class="menu" href="/contact/">Contact</a></nav>
<div class="haut">Bienvenue</div>
<a class="tel" href="tel:0237000000">02 37 00 00 00</a>
<a class="btn-rdv-personnalise rdv" href="/rendez-vous-personnalise/"><span>Rendez-vous personnalisé</span></a>
</body></html>"""


@unittest.skipUnless(os.path.isdir(PW_BROWSERS), "navigateur Playwright absent")
class TestNavigateurLocal(unittest.TestCase):
    def test_bouton_fixe_detecte(self):
        with tempfile.TemporaryDirectory() as d:
            html_path = os.path.join(d, "page.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(FIXED_HTML)
            res = A.run_browser("file://" + html_path, d)
            self.assertIsNone(res.get("erreur"), res.get("erreur"))
            mm = res["vues"]["mobile"]["metriques"]
            self.assertIsNotNone(mm)
            fold = [a for a in mm["appels"] if a["dans_fold"]]
            self.assertTrue(fold, mm["appels"])
            self.assertTrue(all(not a["tel"] for a in fold))
            self.assertTrue(fold[0]["fixe"])
            self.assertIn(fold[0]["motif"], ("texte", "lien vers une page contact", "classe/id"))
            bc = mm["bouton_contact"]
            self.assertTrue(bc["contact_visible_sans_defiler"])
            self.assertFalse(bc["tel_visible_sans_defiler"])
            self.assertTrue(bc["tel_present"])
            self.assertTrue(bc["fixe_visible_sans_defiler"])
            # le lien « Contact » masqué (display:none) n'est pas compté
            self.assertFalse(any(a["texte"] == "Contact" for a in mm["appels"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
