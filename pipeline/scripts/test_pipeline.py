#!/home/user/.venv-webtest/bin/python
"""test_pipeline.py — tests unitaires et de non-régression des scripts du pipeline (lot 1).

Usage : scripts/test_pipeline.py [-v] [-k motif]   (unittest ; code 0 si tout passe)

Couvre :
  - filter_queue.py : cible TPE (effectif, CA, établissements, motifs de nom ; effectif vide gardé), motif
    « hors_cible_taille » dans queue_rejets.csv, en-têtes de queue.csv conservés, option --config ;
  - build_email.py : compteur de mots (méthode documentée dans docs/03), corps ≤ 110 mots, objets sans « site vitrine »,
    aucun chiffre ni score d'outil, aucune prétention de visite humaine, banque de phrases conforme ;
  - build_maquette.py : titre sans ville quand ville et zone manquent, « {metier_court} à {ville} » si la ville est
    présente sans zone, <title> et H1 déduits du spec uniquement ;
  - test_maquette.py : code ≠ 0 si une requête externe est émise ou si le bandeau de démonstration manque
    (Playwright ; la requête externe est bloquée avant d'être émise).
Aucun site tiers n'est consulté : tout tourne sur des fichiers locaux et un serveur HTTP 127.0.0.1.
"""
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ICI = os.path.dirname(os.path.abspath(__file__))
PIPELINE = os.path.dirname(ICI)
PY = sys.executable
sys.path.insert(0, ICI)

import build_email  # noqa: E402
import build_maquette  # noqa: E402
import filter_queue  # noqa: E402

EXEMPLES = os.path.join(PIPELINE, "templates", "exemples")
AUDIT_FACTICE = os.path.join(EXEMPLES, "audit-factice.json")
LEAD_EXEMPLE = os.path.join(EXEMPLES, "lead-exemple.json")
PHRASES = os.path.join(PIPELINE, "templates", "email_phrases.json")
CONFIG = os.path.join(PIPELINE, "config.json")


def lire(chemin):
    with open(chemin, encoding="utf-8") as f:
        return f.read()


def lire_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def ecrire(chemin, contenu):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(contenu)


def ecrire_json(chemin, obj):
    ecrire(chemin, json.dumps(obj, ensure_ascii=False))

COLONNES_ENRICHIS = ["siren", "siret_siege", "nom", "enseigne", "naf", "naf_2025", "forme_juridique", "adresse", "code_postal",
                     "ville", "departement", "latitude", "longitude", "date_creation", "effectif", "categorie", "employeur",
                     "dirigeants", "ca", "resultat_net", "nb_etablissements", "est_rge", "est_bio", "est_ess", "est_qualiopi",
                     "score_lead", "annuaire_url", "site_web", "site_confiance", "emails_publics", "telephones_publics"]


def lead_enrichi(**kw):
    base = {c: "" for c in COLONNES_ENRICHIS}
    base.update({"siren": "000000001", "nom": "TEST PLOMBERIE", "naf": "43.22A", "code_postal": "28000", "ville": "CHARTRES",
                 "departement": "28", "effectif": "02", "categorie": "PME", "ca": "", "nb_etablissements": "1", "score_lead": "20",
                 "site_web": "https://test-plomberie.example", "site_confiance": "haute",
                 "emails_publics": "contact@test-plomberie.example"})
    base.update(kw)
    return base


class TestCibleTPE(unittest.TestCase):
    cible = dict(filter_queue.CIBLE_TPE_DEFAUT)

    def test_effectif(self):
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(effectif="11"), self.cible))   # 10–19 : gardé
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(effectif="00"), self.cible))
        self.assertIn("effectif=12", filter_queue.hors_cible_taille(lead_enrichi(effectif="12"), self.cible) or "")
        self.assertIn("effectif=22", filter_queue.hors_cible_taille(lead_enrichi(effectif="22"), self.cible) or "")

    def test_effectif_vide_garde(self):
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(effectif=""), self.cible))
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(effectif="NN"), self.cible))

    def test_ca_et_etablissements(self):
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(ca="1999999", nb_etablissements="2"), self.cible))
        self.assertIn("ca=2000001", filter_queue.hors_cible_taille(lead_enrichi(ca="2000001"), self.cible) or "")
        self.assertIn("nb_etablissements=3", filter_queue.hors_cible_taille(lead_enrichi(nb_etablissements="3"), self.cible) or "")
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(ca="", nb_etablissements=""), self.cible))

    def test_motifs_nom(self):
        self.assertIn("nom~GROUPE", filter_queue.hors_cible_taille(lead_enrichi(nom="GROUPE ROY ENERGIE"), self.cible) or "")
        self.assertIn("nom~HOLDING", filter_queue.hors_cible_taille(lead_enrichi(nom="X", enseigne="HOLDING DUPONT"), self.cible) or "")
        self.assertIn("nom~SAS INTERNATIONAL", filter_queue.hors_cible_taille(lead_enrichi(nom="SAS INTERNATIONAL TRUC"), self.cible) or "")
        # mot entier seulement : « REGROUPEMENT » ou « GROUPEMENT » ne contiennent pas le mot GROUPE
        self.assertIsNone(filter_queue.hors_cible_taille(lead_enrichi(nom="GROUPEMENT ARTISANS 28"), self.cible))

    def test_config_personnalisee(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = os.path.join(d, "config.json")
            ecrire_json(cfg, {"cible_tpe": {"effectif_max_code": "03", "motifs_exclus_nom": []}})
            c = filter_queue.charger_cible_tpe(cfg)
            self.assertEqual(c["effectif_max_code"], "03")
            self.assertEqual(c["ca_max"], 2000000)        # sous-clé absente : défaut
            self.assertEqual(c["motifs_exclus_nom"], [])
            self.assertIn("effectif=11", filter_queue.hors_cible_taille(lead_enrichi(effectif="11"), c) or "")
        self.assertEqual(filter_queue.charger_cible_tpe("/inexistant/config.json"), filter_queue.CIBLE_TPE_DEFAUT)

    def test_bout_en_bout_fichier(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "enrichis.csv")
            with open(src, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=COLONNES_ENRICHIS, delimiter=";", lineterminator="\n")
                w.writeheader()
                w.writerow(lead_enrichi())
                w.writerow(lead_enrichi(siren="000000002", nom="GROUPE ROY ENERGIE", effectif="22", ca="47311065", nb_etablissements="3",
                                        site_web="https://grouperoyenergie.example", emails_publics="contact@grouperoyenergie.example"))
                w.writerow(lead_enrichi(siren="000000003", nom="SANS EFFECTIF", effectif="", site_web="https://sans-effectif.example",
                                        emails_publics="contact@sans-effectif.example"))
            data = os.path.join(d, "data")
            cfg = os.path.join(d, "config.json")
            ecrire_json(cfg, {"cible_tpe": filter_queue.CIBLE_TPE_DEFAUT})
            cp = subprocess.run([PY, os.path.join(ICI, "filter_queue.py"), src, "--data-dir", data, "--config", cfg],
                                capture_output=True, text=True, timeout=60)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            stats = json.loads(cp.stdout)
            self.assertEqual(stats["exclusions"]["hors_cible_taille"], 1)
            self.assertEqual(stats["sortie"]["total_file"], 2)
            with open(os.path.join(data, "queue.csv"), encoding="utf-8-sig", newline="") as f:
                r = csv.DictReader(f, delimiter=";")
                self.assertEqual(r.fieldnames, filter_queue.COLONNES_QUEUE)
                noms = [x["nom"] for x in r]
            self.assertEqual(sorted(noms), ["SANS EFFECTIF", "TEST PLOMBERIE"])
            with open(os.path.join(data, "queue_rejets.csv"), encoding="utf-8-sig", newline="") as f:
                r = csv.DictReader(f, delimiter=";")
                self.assertEqual(r.fieldnames, filter_queue.COLONNES_REJETS)
                rej = list(r)
            self.assertEqual(len(rej), 1)
            self.assertEqual(rej[0]["nom"], "GROUPE ROY ENERGIE")
            self.assertTrue(rej[0]["motif"].startswith("hors_cible_taille:"), rej[0]["motif"])
            self.assertIn("effectif=22", rej[0]["motif"])

    def test_config_reel(self):
        c = filter_queue.charger_cible_tpe(CONFIG)
        self.assertEqual(c["effectif_max_code"], "11")
        self.assertEqual(c["nb_etablissements_max"], 2)
        self.assertIn("GROUPE", c["motifs_exclus_nom"])


class TestBuildEmail(unittest.TestCase):
    phrases = lire_json(PHRASES)

    def test_compter_mots(self):
        cm = build_email.compter_mots
        self.assertEqual(cm("Bonjour,"), 1)
        self.assertEqual(cm("J'ai testé l'adresse"), 3)             # apostrophes : un seul mot
        self.assertEqual(cm("Nogent-le-Rotrou, à Chartres"), 3)    # trait d'union interne : un seul mot
        self.assertEqual(cm("« Non sécurisé » : rien"), 3)         # guillemets et ponctuation ignorés
        self.assertEqual(cm("https://clientsici.fr/apercu/abc/"), 5)  # une URL : un mot par segment
        self.assertEqual(cm(""), 0)
        self.assertEqual(build_email.MOTS_MAX, 110)

    def _run(self, *args):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "email.json")
            cp = subprocess.run([PY, os.path.join(ICI, "build_email.py"), "--audit", AUDIT_FACTICE, "--lead", LEAD_EXEMPLE,
                                 "--config", CONFIG, "--out", out, *args], capture_output=True, text=True, timeout=120)
            res = lire_json(out) if os.path.exists(out) else None
        return cp.returncode, json.loads(cp.stdout), res

    def test_email_fixtures_sans_et_avec_maquette(self):
        for extra in ((), ("--maquette-url", "https://clientsici.fr/apercu/abcdefghij0123456789/")):
            for graine in range(1, 9):
                code, ligne, res = self._run("--graine", str(graine), *extra)
                self.assertEqual(code, 0, ligne)
                self.assertTrue(res["controles"]["ok"], res["controles"])
                self.assertLessEqual(res["nb_mots_corps"], 110)
                self.assertGreaterEqual(res["nb_mots_corps"], 80)
                self.assertEqual(res["nb_mots_corps"], build_email.compter_mots(res["corps"]))
                for o in res["objets"]:
                    self.assertNotIn("site vitrine", o.lower(), o)
                    self.assertLessEqual(len(o), 50)
                sans_url = res["corps"].replace(res.get("maquette_url") or "", "").replace(res["lead"]["domaine"], "")
                self.assertFalse(re.search(r"\d", sans_url), res["corps"])
                self.assertFalse(re.search(r"lighthouse|/100|score", res["corps"], re.I), res["corps"])
                for t in (res["corps"], res["whatsapp"]["texte"], res["sms"]["texte"]):
                    self.assertFalse(build_email.MOTIFS_VISITE.search(t), t)
                self.assertEqual(res["corps"].count("?"), 1)

    def test_controles_detectent(self):
        pb = build_email.controler(["votre site vitrine sur téléphone"], "Bonjour, je suis passé sur votre site, score 61/100 ?",
                                   None, "x.example", autres_textes=("Depuis mon téléphone, bonjour.",))
        texte = " | ".join(pb)
        self.assertIn("site vitrine", texte)
        self.assertIn("prétention de visite humaine (corps)", texte)
        self.assertIn("prétention de visite humaine (texte 1)", texte)
        self.assertIn("mesure ou score", texte)
        self.assertIn("chiffre dans le corps", texte)

    def test_banque_de_phrases(self):
        p = self.phrases
        for o in p["objets_generiques"] + [o for c in p["categories"].values() for o in c.get("objets", [])]:
            self.assertNotIn("site vitrine", o.lower(), o)
        textes = p["ouvertures"] + p["benefices"] + p["maquette_avec_url"] + p["maquette_sans_url"] + p["whatsapp"] + p["sms"] \
            + [x for c in p["categories"].values() for x in c["constats"] + c["courts"]]
        for t in textes:
            self.assertFalse(build_email.MOTIFS_VISITE.search(t), t)
            self.assertFalse(re.search(r"lighthouse|/100|\d", t, re.I), t)
            self.assertNotIn("—", t)
        for cle in ("perf_faible", "perf_moyenne", "poids", "score_lh"):
            for t in p["categories"][cle]["constats"]:
                self.assertFalse(re.search(r"mesur|score|\d", t, re.I), t)   # lenteur = constat sans chiffre ni mesure citée


class TestBuildMaquette(unittest.TestCase):
    def ctx(self, **spec):
        base = {"nom": "Exemple Test", "palette": "batiment", "objectif": "devis"}
        base.update(spec)
        return build_maquette.construire_contexte(base, [], None, "Clients Ici")

    def test_titre_sans_ville_ni_zone(self):
        c = self.ctx(metier="Travaux de peinture", metier_court="Peintre")
        self.assertEqual(c["titre_hero"], "Peintre")
        self.assertNotIn(" à ", c["titre_hero"])
        self.assertEqual(c["titre_page"], "Peintre | Exemple Test (maquette)")
        self.assertIsNone(c["ville"])
        self.assertIsNone(c["zone"])

    def test_titre_ville_sans_zone(self):
        c = self.ctx(metier_court="Peintre", ville="Dreux")
        self.assertEqual(c["titre_hero"], "Peintre à Dreux")
        self.assertIsNone(c["zone"])

    def test_titre_zone_sans_ville(self):
        c = self.ctx(metier_court="Peintre", zone="Dreux et alentours (texte du site)")
        self.assertEqual(c["titre_hero"], "Peintre")

    def test_titre_sans_metier(self):
        self.assertEqual(self.ctx()["titre_hero"], "Exemple Test")

    def test_verifier_titre_refuse_lieu_invente(self):
        with self.assertRaises(ValueError):
            build_maquette.verifier_titre("Peintre à Dreux", {"metier_court": "Peintre", "nom": "X", "ville": None})
        with self.assertRaises(ValueError):
            build_maquette.verifier_titre("Meilleur peintre", {"metier_court": "Peintre", "nom": "X", "ville": "Dreux"})

    def test_title_et_h1_dans_le_html(self):
        with tempfile.TemporaryDirectory() as d:
            spec = os.path.join(d, "spec.json")
            ecrire_json(spec, {"nom": "Exemple Test", "metier": "Salon de coiffure", "palette": "service", "objectif": "appel"})
            out = os.path.join(d, "m", "index.html")
            cp = subprocess.run([PY, os.path.join(ICI, "build_maquette.py"), "--spec", spec, "--out", out], capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stdout)
            html = lire(out)
            self.assertIn("<title>Salon de coiffure | Exemple Test (maquette)</title>", html)
            self.assertIn('<h1 id="titre-principal">Salon de coiffure</h1>', html)
            self.assertNotRegex(html, r"<h1[^>]*>[^<]*\bà\b")


class TestTestMaquette(unittest.TestCase):
    """test_maquette.py doit renvoyer 1 pour une maquette fautive (Playwright, serveur local uniquement)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with tempfile.TemporaryDirectory() as d:
            spec = os.path.join(d, "spec.json")
            ecrire_json(spec, {"nom": "Exemple Test", "metier_court": "Peintre", "ville": "Dreux", "tel": "02 00 00 00 00",
                       "palette": "batiment", "objectif": "devis"})
            cp = subprocess.run([PY, os.path.join(ICI, "build_maquette.py"), "--spec", spec,
                                 "--out", os.path.join(cls.tmp.name, "ok", "index.html")], capture_output=True, text=True)
            assert cp.returncode == 0, cp.stdout
        cls.html_ok = lire(os.path.join(cls.tmp.name, "ok", "index.html"))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _tester(self, nom, html):
        d = os.path.join(self.tmp.name, nom)
        ecrire(os.path.join(d, "index.html"), html)
        cp = subprocess.run([PY, os.path.join(ICI, "test_maquette.py"), d], capture_output=True, text=True, timeout=300)
        return cp.returncode, json.loads(cp.stdout)

    def test_maquette_correcte_passe(self):
        code, res = self._tester("ok", self.html_ok)
        self.assertEqual(code, 0, res)
        self.assertEqual(res["ko_total"], 0)

    def test_requete_externe_fait_echouer(self):
        html = self.html_ok.replace("</main>", '<img src="https://exemple-externe.invalid/pixel.png" alt=""></main>', 1)
        self.assertNotEqual(html, self.html_ok)
        code, res = self._tester("externe", html)
        self.assertEqual(code, 1)
        ko = " | ".join(res["maquettes"]["externe"]["ko"])
        self.assertIn("requête(s) externe(s) bloquée(s)", ko)
        self.assertIn("exemple-externe.invalid", ko)

    def test_bandeau_absent_fait_echouer(self):
        html = re.sub(r'<div class="avis".*?</div>\s*</div>', "", self.html_ok, count=1, flags=re.S)
        self.assertNotIn("Proposition non officielle", html.split("<footer")[0])
        code, res = self._tester("sansbandeau", html)
        self.assertEqual(code, 1)
        self.assertIn("bandeau de démonstration absent", " | ".join(res["maquettes"]["sansbandeau"]["ko"]))


if __name__ == "__main__":
    unittest.main(verbosity=2 if "-v" in sys.argv else 1, argv=[a for a in sys.argv if a != "-v"])
