#!/home/user/.venv-webtest/bin/python
# -*- coding: utf-8 -*-
"""
audit_site.py — Audit automatique, en lecture seule, du site d'un prospect.

Usage :
    audit_site.py <url> --out <dossier> [--pages 4] [--ville "Chartres"] [--cp 28000]
                  [--nom "SARL Dupont"] [--enseigne "Dupont Plomberie"] [--siren 123456789]
                  [--metier "plombier chauffagiste"]
                  [--no-browser] [--no-lighthouse] [--timeout 12]

Produit dans <dossier> : audit.json, audit.md, captures/*.png, lighthouse.json.
Ligne JSON de résumé sur stdout : url, domaine_demande, domaine_final (hôte de l'URL finale),
verdict, constats, gravites, lighthouse_performance, correspondance_entreprise (éléments du
lead retrouvés sur le site : nom, enseigne, ville, cp, siren), duree_s, out, erreurs.
Code de sortie : 0 si audit.json a été écrit (même avec des étapes « non mesurées »),
2 si les arguments sont invalides, 1 en cas d'erreur fatale avant écriture.

Règles respectées : lecture seule, User-Agent identifiable, au plus 8 requêtes HTML
par site (+ robots.txt, sitemap.xml et les ressources chargées par le navigateur),
délais courts, aucune donnée inventée : tout ce qui n'a pas pu être mesuré est
marqué « non mesuré » ou « non vérifié ».
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------

USER_AGENT = "Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/)"
MAX_HTML_REQUESTS = 8          # budget de requêtes HTML par site (hors robots/sitemap)
MAX_BODY_BYTES = 3_000_000     # taille max lue par page HTML
DEFAULT_TIMEOUT = 12           # secondes (connexion + lecture)
BROWSER_NAV_TIMEOUT_MS = 30_000
LIGHTHOUSE_TIMEOUT_S = 180
MAX_FULLPAGE_HEIGHT = 12_000   # px : au-delà, la capture pleine page est tronquée

DEFAULT_PW_BROWSERS = "/home/user/.venv-webtest/ms-playwright"
DEFAULT_CHROME_PATH = "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome"

VIEWPORTS = [
    {"nom": "mobile", "width": 375, "height": 812, "mobile": True, "scale": 2},
    {"nom": "desktop", "width": 1440, "height": 900, "mobile": False, "scale": 1},
]

# Mots-clés pour retenir les pages internes pertinentes (score sur href + texte)
PAGE_KEYWORDS = [
    (r"contact|nous-joindre|joindre|coordonn", "contact", 10),
    (r"devis|demande", "devis", 9),
    (r"service|prestation|savoir-faire|metier|métier|activit|nos-offres|offre", "services", 8),
    (r"a-propos|apropos|à-propos|qui-sommes|qui-suis|entreprise|histoire|presentation|présentation|equipe|équipe|about", "a-propos", 7),
    (r"realisation|réalisation|galerie|photos|portfolio|reference|référence|chantier|travaux|projets", "realisations", 7),
    (r"tarif|prix", "tarifs", 5),
    (r"horaire|acces|accès", "horaires", 3),
]
# Pages qui ne décrivent pas des prestations : jamais classées « services », jamais sources de services_listes
NON_SERVICE_PAGE_RE = re.compile(r"recrut|emploi|carri[èe]re|job|candidat|offre[s]?-d|actualit|blog|news|presse|article|mention|legal|légal", re.I)
# Titres H2/H3 à ne pas prendre pour des prestations (sections génériques, appels à l'action, questions)
NON_SERVICE_TITLE_RE = re.compile(
    r"contact|mentions|cookies|newsletter|suivez|partag|coordonn|formulaire|rendez-vous|inscri|t[ée]moignage|avis|"
    r"actualit|blog|vid[ée]o|rejoignez|recrut|emploi|carri[èe]re|offre[s]? d|confiance|votre projet|votre demande|"
    r"questions? fr[ée]quente|\bfaq\b|^[àa] lire|€|payez|tarif|prix|"
    r"^(demande[rz]|obten(ez|ir)|contactez|d[ée]couvr(ez|ir)|t[ée]l[ée]charge[rz]|en savoir|ils nous|nous sommes|"
    r"je |nous |vous |on |pourquoi|comment|qu['’]est|quel(le|s)?\b|où\b|qui (sommes|est|suis)|à propos|a propos|bienvenue)",
    re.I,
)
# Titres introduisant une liste de prestations (ul/li qui suit)
SERVICE_LIST_HEADING_RE = re.compile(r"prestation|service|nos m[ée]tiers|savoir-faire|sp[ée]cialit|domaines? d['’]intervention|nos activit|nos offres|nos solutions|nos interventions", re.I)
MAX_SERVICES = 12
EXCLUDED_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".doc", ".docx", ".xls", ".xlsx", ".mp4", ".mp3", ".txt", ".xml", ".json", ".rss", ".ics")
EXCLUDED_PATH = re.compile(r"mentions|legal|légal|cgv|cgu|confidentialit|cookies|plan-du-site|sitemap|wp-login|wp-admin|/feed|/tag/|/category/|/author/|\?s=|/panier|/cart|/login|/connexion|/compte", re.I)

# Générateurs de site : (motif dans le HTML, nom, gratuit/grand public ?)
GENERATORS = [
    (r"wp-content/|wp-includes/|wordpress", "WordPress", False),
    (r"wixstatic\.com|wix\.com|wixsite\.com|_wix_|wix-", "Wix", True),
    (r"jimdo", "Jimdo", True),
    (r"squarespace", "Squarespace", False),
    (r"weebly", "Weebly", True),
    (r"site123", "SITE123", True),
    (r"webself", "Webself", True),
    (r"e-monsite|emonsite", "e-monsite", True),
    (r"sites\.google\.com|googleusercontent\.com/sites", "Google Sites", True),
    (r"wifeo", "Wifeo", True),
    (r"sitew\.", "SiteW", True),
    (r"strikingly", "Strikingly", True),
    (r"webnode", "Webnode", True),
    (r"one\.com|onewebmedia|mono\.net|monosolutions", "one.com / Mono", False),
    (r"ionos|1and1|1&1", "IONOS MyWebsite", False),
    (r"godaddy|secureserver\.net|wsimg\.com", "GoDaddy", False),
    (r"simplebo|simplébo", "Simplébo", False),
    (r"solocal|pagesjaunes|site-privilege|visibilite-pro", "Solocal / PagesJaunes", False),
    (r"duda|dudamobile|multiscreensite", "Duda", False),
    (r"webflow", "Webflow", False),
    (r"hubspot", "HubSpot CMS", False),
    (r"shopify", "Shopify", False),
    (r"prestashop", "PrestaShop", False),
    (r"joomla", "Joomla", False),
    (r"drupal", "Drupal", False),
    (r"typo3", "TYPO3", False),
    (r"wordpress\.com", "WordPress.com", True),
    (r"blogspot|blogger", "Blogger", True),
    (r"orange\.fr/|pagesperso-orange", "Pages perso Orange", True),
    (r"free\.fr", "Pages perso Free", True),
]

LOCALBUSINESS_TYPES = {
    "LocalBusiness", "HomeAndConstructionBusiness", "Plumber", "Electrician", "RoofingContractor",
    "HousePainter", "GeneralContractor", "Locksmith", "HVACBusiness", "MovingCompany", "Store",
    "Restaurant", "Bakery", "HairSalon", "BeautySalon", "Dentist", "AutoRepair", "AutoDealer",
    "ProfessionalService", "FoodEstablishment", "MedicalBusiness", "Florist", "Optician",
    "RealEstateAgent", "TravelAgency", "DryCleaningOrLaundry", "SportsActivityLocation",
    "HealthAndBeautyBusiness", "LegalService", "FinancialService", "AutomotiveBusiness",
    "LodgingBusiness", "EntertainmentBusiness", "ChildCare", "AnimalShelter", "Dentist",
    "Physician", "Pharmacy", "Hotel", "Cafe", "CafeOrCoffeeShop", "BarOrPub", "Butcher",
    "GroceryStore", "ClothingStore", "FurnitureStore", "HardwareStore", "GardenStore",
    "ElectronicsStore", "ShoeStore", "JewelryStore", "PetStore", "BikeStore", "BookStore",
    "Winery", "Brewery", "Notary", "Attorney", "AccountingService", "InsuranceAgency",
    "DaySpa", "NailSalon", "TattooParlor", "Landscaper", "SelfStorage", "EmploymentAgency",
    "AutoBodyShop", "AutoWash", "GasStation", "MotorcycleDealer", "MotorcycleRepair",
    "Dentist", "VeterinaryCare",
}

DEPARTEMENTS = [
    "Ain", "Aisne", "Allier", "Alpes-de-Haute-Provence", "Hautes-Alpes", "Alpes-Maritimes", "Ardèche",
    "Ardennes", "Ariège", "Aube", "Aude", "Aveyron", "Bouches-du-Rhône", "Calvados", "Cantal", "Charente",
    "Charente-Maritime", "Cher", "Corrèze", "Corse", "Côte-d'Or", "Côtes-d'Armor", "Creuse", "Dordogne",
    "Doubs", "Drôme", "Eure", "Eure-et-Loir", "Finistère", "Gard", "Haute-Garonne", "Gers", "Gironde",
    "Hérault", "Ille-et-Vilaine", "Indre", "Indre-et-Loire", "Isère", "Jura", "Landes", "Loir-et-Cher",
    "Loire", "Haute-Loire", "Loire-Atlantique", "Loiret", "Lot", "Lot-et-Garonne", "Lozère",
    "Maine-et-Loire", "Manche", "Marne", "Haute-Marne", "Mayenne", "Meurthe-et-Moselle", "Meuse",
    "Morbihan", "Moselle", "Nièvre", "Nord", "Oise", "Orne", "Pas-de-Calais", "Puy-de-Dôme",
    "Pyrénées-Atlantiques", "Hautes-Pyrénées", "Pyrénées-Orientales", "Bas-Rhin", "Haut-Rhin", "Rhône",
    "Haute-Saône", "Saône-et-Loire", "Sarthe", "Savoie", "Haute-Savoie", "Paris", "Seine-Maritime",
    "Seine-et-Marne", "Yvelines", "Deux-Sèvres", "Somme", "Tarn", "Tarn-et-Garonne", "Var", "Vaucluse",
    "Vendée", "Vienne", "Haute-Vienne", "Vosges", "Yonne", "Territoire de Belfort", "Essonne",
    "Hauts-de-Seine", "Seine-Saint-Denis", "Val-de-Marne", "Val-d'Oise", "Guadeloupe", "Martinique",
    "Guyane", "La Réunion", "Mayotte", "Île-de-France", "Normandie", "Bretagne", "Centre-Val de Loire",
    "Perche", "Beauce",
]

ZONE_PATTERNS = re.compile(
    r"\b(intervient|intervenons|interviens|intervention[s]?\s+(?:sur|dans|à|a)|secteur\s+d|zone\s+d['’]intervention|"
    r"rayon\s+de\s+\d+\s*km|km\s+autour|alentours|et\s+ses\s+environs|et\s+environs|dans\s+(?:le|la|les|tout\s+le)\s+"
    r"(?:département|departement|région|region|agglomération|agglomeration)|aux\s+alentours|près\s+de\s+chez\s+vous|"
    r"proche\s+de\s+chez\s+vous)",
    re.I,
)

# Numéro français : un seul séparateur, répété à l'identique (évite de lire « 05 2026-09-15 » dans une date)
PHONE_RE = re.compile(r"(?<!\d)(?:\+33\s?\(?0?\)?\s?|0)[1-9](?P<sep>[\s.\-]?)\d{2}(?:(?P=sep)\d{2}){3}(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
CP_VILLE_RE = re.compile(
    r"(?<![\d\w])(\d{5})\s+((?:[A-ZÀ-ÝŒ][A-Za-zÀ-ÿœ'’\-]+|[A-ZÀ-ÝŒ]{2,})(?:[\s\-](?:[A-ZÀ-ÝŒ][A-Za-zÀ-ÿœ'’\-]+|[A-ZÀ-ÝŒ]{2,}|sur|sous|en|le|la|les|de|du|des|lès|aux|d['’][A-ZÀ-Ý][a-zà-ÿ]+)){0,4})"
)
STREET_RE = re.compile(
    r"(\d{1,4}\s?(?:bis|ter)?,?\s+(?:rue|avenue|av\.?|boulevard|bd\.?|place|chemin|route|impasse|allée|allee|"
    r"lieu-dit|hameau|quai|cours|square|zone\s+(?:artisanale|industrielle)|za|zi|rd|d\d+)\b[^\n,;|<>]{2,60}?)\s*[,\-–]?\s*$",
    re.I,
)
COPYRIGHT_RE = re.compile(r"(?:©|&copy;|\(c\)|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", re.I)
DEVIS_RE = re.compile(r"\bdevis\b", re.I)
URGENCE_RE = re.compile(r"\burgen(?:ce|ces|t|te|ts|tes)\b", re.I)



def _ou_tel(tel_any, home_url):
    """Décrit où se trouve le lien tel: sans affirmer qu'il est sur l'accueil s'il n'y est pas."""
    if not tel_any:
        return "aucun lien tel: sur les pages consultées"
    pages_tel = [p for p in tel_any if p.get("liens_tel")]
    if any(p.get("url") == home_url for p in pages_tel):
        return "lien tel: présent plus bas sur la page d'accueil"
    autres = [p.get("url") for p in pages_tel if p.get("url")]
    return "lien tel: présent seulement sur " + ", ".join(autres[:2]) if autres else "lien tel: présent sur une autre page"

def log(msg: str) -> None:
    sys.stderr.write(f"[audit] {msg}\n")
    sys.stderr.flush()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------
# Collecte HTTP
# ----------------------------------------------------------------------------

class Collector:
    """Session HTTP en lecture seule avec budget de requêtes."""

    def __init__(self, timeout: int):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.5",
        })
        self.timeout = timeout
        self.html_requests = 0
        self.other_requests = 0
        self.journal: list[dict] = []

    def _record(self, kind: str, url: str, res: dict) -> None:
        self.journal.append({"type": kind, "url": url, "status": res.get("status"),
                             "final_url": res.get("final_url"), "duree_s": res.get("duree_s"),
                             "erreur": res.get("erreur")})

    def get(self, url: str, kind: str = "html", read_body: bool = True) -> dict:
        """GET avec suivi de redirections. Retourne un dict stable, jamais d'exception."""
        res = {"url": url, "status": None, "final_url": None, "chaine": [], "headers": {},
               "body": None, "content_type": None, "duree_s": None, "erreur": None}
        if kind == "html":
            if self.html_requests >= MAX_HTML_REQUESTS:
                res["erreur"] = "budget de requêtes HTML épuisé"
                self._record(kind, url, res)
                return res
            self.html_requests += 1
        else:
            self.other_requests += 1
        t0 = time.time()
        try:
            r = self.s.get(url, timeout=self.timeout, allow_redirects=True, stream=True)
            res["chaine"] = [{"url": h.url, "status": h.status_code, "location": h.headers.get("Location")}
                             for h in r.history]
            res["status"] = r.status_code
            res["final_url"] = r.url
            res["headers"] = {k.lower(): v for k, v in r.headers.items()}
            res["content_type"] = (r.headers.get("Content-Type") or "").lower()
            if read_body:
                chunks, total = [], 0
                for chunk in r.iter_content(chunk_size=65536):
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= MAX_BODY_BYTES:
                        res["tronque"] = True
                        break
                raw = b"".join(chunks)
                enc = None
                if "charset=" in res["content_type"]:
                    enc = res["content_type"].split("charset=")[-1].split(";")[0].strip().strip('"')
                res["body_bytes"] = raw
                res["encodage_declare"] = enc
                res["taille_octets"] = len(raw)
            r.close()
        except requests.exceptions.Timeout:
            res["erreur"] = f"délai dépassé ({self.timeout} s)"
        except requests.exceptions.SSLError as e:
            res["erreur"] = f"erreur TLS : {str(e)[:160]}"
        except requests.exceptions.ConnectionError as e:
            res["erreur"] = f"connexion impossible : {str(e)[:160]}"
        except requests.exceptions.TooManyRedirects:
            res["erreur"] = "trop de redirections"
        except Exception as e:  # noqa: BLE001
            res["erreur"] = f"{type(e).__name__} : {str(e)[:160]}"
        res["duree_s"] = round(time.time() - t0, 2)
        self._record(kind, url, res)
        return res


def normalize_url(u: str) -> str:
    p = urlparse(u)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", p.query, ""))


def host_base(netloc: str) -> str:
    h = netloc.lower().split(":")[0]
    return h[4:] if h.startswith("www.") else h


def same_site(a: str, b: str) -> bool:
    return host_base(urlparse(a).netloc) == host_base(urlparse(b).netloc)


# ----------------------------------------------------------------------------
# Analyse d'une page HTML
# ----------------------------------------------------------------------------

def visible_text(soup: BeautifulSoup) -> str:
    for t in soup(["script", "style", "noscript", "template", "svg", "select"]):
        t.decompose()
    txt = soup.get_text(" ")
    return re.sub(r"[ \t\r\f\v]+", " ", re.sub(r"\n+", "\n", txt)).strip()


def detect_generator(html_lower: str, meta_generator: str | None) -> dict:
    found = []
    if meta_generator:
        found.append({"nom": meta_generator.strip()[:80], "source": "meta generator", "gratuit": None})
    for pat, nom, gratuit in GENERATORS:
        if re.search(pat, html_lower):
            if not any(f["nom"].lower().startswith(nom.lower().split()[0]) for f in found):
                found.append({"nom": nom, "source": "traces dans le HTML", "gratuit": gratuit})
    gratuit = any(f.get("gratuit") for f in found)
    for f in found:
        if f["gratuit"] is None:
            f["gratuit"] = any(f["nom"].lower().startswith(nom.lower().split()[0]) and g for _, nom, g in GENERATORS)
    return {"detectes": found, "generateur_gratuit": gratuit}


def jsonld_types(soup: BeautifulSoup) -> tuple[list[str], list[str]]:
    types, errors = [], []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types.extend([x for x in t if isinstance(x, str)])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for sc in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw = (sc.string or sc.get_text() or "").strip()
        if not raw:
            continue
        try:
            walk(json.loads(raw))
        except Exception:
            try:
                walk(json.loads(re.sub(r"^\s*<!--|-->\s*$", "", raw)))
            except Exception as e:  # noqa: BLE001
                errors.append(f"JSON-LD illisible : {type(e).__name__}")
    return types, errors


def extract_addresses(text: str) -> list[dict]:
    out, seen = [], set()
    for m in CP_VILLE_RE.finditer(text):
        cp, ville = m.group(1), m.group(2).strip(" -")
        if not ("01000" <= cp <= "98999"):
            continue
        if ville.lower() in {"france", "cedex"} or len(ville) < 2:
            continue
        ville = re.sub(r"\s+(cedex|france|tél|tel|téléphone|telephone|siret|tva|itin[ée]raire|horaires?|ouvert|contact|e-?mail|courriel|voir|plan|nous|appel\w*|devis|accueil|agence).*$", "", ville, flags=re.I).strip()
        if not ville:
            continue
        key = (cp, ville.lower())
        if key in seen:
            continue
        seen.add(key)
        before = text[max(0, m.start() - 90): m.start()]
        rue = None
        sm = STREET_RE.search(before)
        if sm:
            rue = re.sub(r"\s+", " ", sm.group(1)).strip(" ,-")
        out.append({"rue": rue, "code_postal": cp, "ville": ville})
        if len(out) >= 5:
            break
    return out


def heading_text(h) -> str:
    """Texte d'un titre : les lignes d'un titre multi-lignes (<br>) sont jointes par un espace."""
    for br in h.find_all("br"):
        br.replace_with(" ")
    return re.sub(r"\s+", " ", h.get_text(" ", strip=True)).strip()


def clean_service_title(t: str) -> str | None:
    """Retourne le titre nettoyé s'il peut désigner une prestation, sinon None."""
    t = re.sub(r"\s+", " ", (t or "").replace("\xa0", " ")).strip(" \t-–—:;·•")
    if not (3 <= len(t) <= 70):
        return None
    if t.endswith((",", "?", "…", "...", ":", ";")):
        return None
    if NON_SERVICE_TITLE_RE.search(t):
        return None
    mots = t.split()
    if len(mots) > 6:                                   # une prestation tient en quelques mots ; au-delà, c'est une phrase
        return None
    if len(mots) >= 4 and t == t.upper() and re.search(r"[A-ZÀ-Ý]{3}", t):   # slogan tout en majuscules
        return None
    if re.fullmatch(r"(nos |vos |les |notre )?(solutions?|services?|prestations?|r[ée]alisations?|m[ée]tiers?|savoir-faire|activit[ée]s?|offres?|produits?|expertises?|domaines?)", t, re.I):
        return None                                      # intitulé de section générique, pas une prestation
    return t
    if re.search(r"\d{2}[\s.]\d{2}[\s.]\d{2}", t) or "@" in t:   # numéro ou e-mail dans le titre
        return None
    return t


def extract_service_lists(soup: BeautifulSoup) -> list[dict]:
    """ul/ol qui suivent un H2/H3 contenant prestation|service|nos métiers|savoir-faire… (hors formulaire, hors nav)."""
    out = []
    for h in soup.find_all(["h2", "h3"]):
        if h.find_parent("form") or h.find_parent("nav"):
            continue
        titre = heading_text(h)
        if not SERVICE_LIST_HEADING_RE.search(titre):
            continue
        nxt = h.find_next(["ul", "ol", "h1", "h2", "h3", "form"])
        if nxt is None or nxt.name not in ("ul", "ol") or nxt.find_parent("nav") or nxt.find_parent("form"):
            continue
        items = []
        for li in nxt.find_all("li", recursive=False):
            t = re.sub(r"\s+", " ", li.get_text(" ", strip=True)).strip()
            t = clean_service_title(t)
            if t and t not in items:
                items.append(t)
        if items:
            out.append({"titre": titre[:120], "elements": items[:MAX_SERVICES]})
        if len(out) >= 4:
            break
    return out


def normalize_phone(p: str) -> str:
    d = re.sub(r"\D", "", p)
    if d.startswith("33"):
        d = "0" + d[2:]
    if d.startswith("330"):
        d = "0" + d[3:]
    if len(d) != 10:
        return p.strip()
    return " ".join(d[i:i + 2] for i in range(0, 10, 2))


def analyse_page(url: str, res: dict, role: str) -> dict:
    page = {
        "role": role, "url": url, "final_url": res.get("final_url"), "status": res.get("status"),
        "content_type": res.get("content_type"), "taille_octets": res.get("taille_octets"),
        "duree_s": res.get("duree_s"), "erreur": res.get("erreur"), "html": False,
    }
    body = res.get("body_bytes")
    if body is None or res.get("status") is None:
        return page
    if "html" not in (res.get("content_type") or "") and not body[:300].lower().lstrip().startswith((b"<!doctype", b"<html")):
        page["erreur"] = page["erreur"] or f"contenu non HTML ({res.get('content_type')})"
        return page
    try:
        soup = BeautifulSoup(body, "lxml", from_encoding=res.get("encodage_declare") or None)
    except Exception as e:  # noqa: BLE001
        page["erreur"] = f"analyse HTML impossible : {type(e).__name__}"
        return page
    page["html"] = True
    html_lower = body.decode("utf-8", errors="ignore").lower()

    head = soup.head or soup
    title_tag = soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else None
    page["title"] = title
    page["title_longueur"] = len(title) if title else 0

    def meta(name=None, prop=None):
        if name:
            m = head.find("meta", attrs={"name": re.compile(rf"^{re.escape(name)}$", re.I)})
        else:
            m = head.find("meta", attrs={"property": re.compile(rf"^{re.escape(prop)}$", re.I)})
        return m.get("content").strip() if m and m.get("content") else None

    desc = meta("description")
    page["meta_description"] = desc
    page["meta_description_longueur"] = len(desc) if desc else 0
    page["meta_viewport"] = meta("viewport")
    page["meta_robots"] = meta("robots")
    page["meta_generator"] = meta("generator")
    page["og_title"] = meta(prop="og:title")
    html_tag = soup.find("html")
    page["lang"] = (html_tag.get("lang") or "").strip() or None if html_tag else None
    can = head.find("link", attrs={"rel": lambda v: v and "canonical" in [x.lower() for x in (v if isinstance(v, list) else [v])]})
    page["canonical"] = can.get("href") if can else None
    h1s = [heading_text(h) for h in soup.find_all("h1")]
    page["h1"] = h1s
    page["h1_nombre"] = len(h1s)
    page["h2"] = [heading_text(h)[:120] for h in soup.find_all("h2")][:20]
    page["h3"] = [heading_text(h)[:120] for h in soup.find_all("h3")][:30]
    # Titres H2/H3 hors formulaire (candidats « services ») et listes de prestations (ul/li sous un titre évocateur)
    page["_titres_hors_formulaire"] = [heading_text(h) for h in soup.find_all(["h2", "h3"]) if not h.find_parent("form")][:60]
    page["_listes_prestations"] = extract_service_lists(soup)

    # Liens
    base = res.get("final_url") or url
    internal, external, tel_links, mailto_links, nav_links = [], [], [], [], []
    nav_zone = soup.find_all(["nav", "header", "footer"])
    nav_anchor_ids = set(id(a) for z in nav_zone for a in z.find_all("a", href=True))
    for a in soup.find_all("a", href=True):
        href = a.get("href").strip()
        low = href.lower()
        if low.startswith("tel:"):
            tel_links.append(href)
            continue
        if low.startswith("mailto:"):
            mailto_links.append(href)
            continue
        if low.startswith(("javascript:", "#", "sms:", "whatsapp:", "data:")) or not href:
            continue
        absu = urljoin(base, href)
        if not absu.startswith(("http://", "https://")):
            continue
        text = a.get_text(" ", strip=True)[:80]
        entry = {"url": absu, "texte": text, "nav": id(a) in nav_anchor_ids}
        if same_site(absu, base):
            internal.append(entry)
            if entry["nav"]:
                nav_links.append(entry)
        else:
            external.append(entry)
    page["liens_internes"] = len(internal)
    page["liens_externes"] = len(external)
    page["liens_tel"] = sorted(set(tel_links))
    page["liens_mailto"] = sorted(set(mailto_links))
    page["_internal_links"] = internal
    page["_nav_links"] = nav_links

    # Images
    imgs = soup.find_all("img")
    sans_alt = [(im.get("src") or im.get("data-src") or "")[:120] for im in imgs
                if im.get("alt") is None or im.get("alt").strip() == ""]
    page["images_total"] = len(imgs)
    page["images_sans_alt"] = len(sans_alt)
    page["images_sans_alt_exemples"] = sans_alt[:5]

    # Scripts externes
    ext_scripts = []
    for sc in soup.find_all("script", src=True):
        src = urljoin(base, sc.get("src"))
        if not same_site(src, base):
            ext_scripts.append(urlparse(src).netloc)
    page["scripts_externes"] = len(ext_scripts)
    page["scripts_externes_domaines"] = sorted(set(ext_scripts))[:15]

    page["generateur"] = detect_generator(html_lower, page["meta_generator"])
    types, jerr = jsonld_types(soup)
    page["jsonld_types"] = sorted(set(types))
    page["jsonld_erreurs"] = jerr
    page["jsonld_localbusiness"] = any(t in LOCALBUSINESS_TYPES or t.endswith(("Business", "Store", "Salon", "Contractor", "Shop")) for t in types)

    text = visible_text(soup)
    page["_text"] = text
    page["texte_longueur_mots"] = len(text.split())
    phones = []
    for m in PHONE_RE.finditer(text + " " + " ".join(tel_links)):
        p = normalize_phone(m.group(0))
        if p not in phones:
            phones.append(p)
    page["telephones_detectes"] = phones[:5]
    emails = []
    for m in EMAIL_RE.finditer(text + " " + " ".join(mailto_links)):
        e = m.group(0).lower().rstrip(".")
        if e not in emails and not e.endswith((".png", ".jpg", ".svg", ".webp", ".gif", ".css", ".js")):
            emails.append(e)
    page["emails_detectes"] = emails[:5]
    page["adresses_detectees"] = extract_addresses(text)
    page["mention_devis"] = bool(DEVIS_RE.search(text))
    page["mention_urgence"] = bool(URGENCE_RE.search(text))
    years = [int(y) for y in COPYRIGHT_RE.findall(body.decode("utf-8", errors="ignore"))]
    page["copyright_annee"] = max(years) if years else None
    deps = [d for d in DEPARTEMENTS if re.search(rf"(?<![\w-]){re.escape(d)}(?![\w-])", text)]
    page["departements_mentionnes"] = deps[:5]
    page["mention_zone"] = bool(ZONE_PATTERNS.search(text))
    return page


# ----------------------------------------------------------------------------
# Choix des pages internes
# ----------------------------------------------------------------------------

def choose_internal_pages(home: dict, max_pages: int) -> list[dict]:
    if max_pages <= 0 or not home.get("html"):
        return []
    home_norm = normalize_url(home.get("final_url") or home["url"])
    scores: dict[str, dict] = {}
    for link in home.get("_internal_links", []):
        u = link["url"]
        p = urlparse(u)
        if p.path.lower().endswith(EXCLUDED_EXT) or EXCLUDED_PATH.search(u):
            continue
        n = normalize_url(u)
        if n == home_norm:
            continue
        hay = (p.path + " " + p.query + " " + link["texte"]).lower()
        non_service = bool(NON_SERVICE_PAGE_RE.search(hay))
        best_cat, best = None, 0
        for pat, cat, w in PAGE_KEYWORDS:
            if cat == "services" and non_service:   # recrutement, emploi, carrière, actualités… ne sont pas des pages services
                continue
            if re.search(pat, hay):
                if w > best:
                    best, best_cat = w, cat
        if best == 0 and not link["nav"]:
            continue
        score = best + (2 if link["nav"] else 0)
        cat = best_cat or "navigation"
        cur = scores.get(n)
        if not cur or score > cur["score"]:
            scores[n] = {"url": u, "categorie": cat, "score": score, "texte": link["texte"]}
    # une page par catégorie d'abord, puis les meilleures restantes
    ranked = sorted(scores.values(), key=lambda x: (-x["score"], x["url"]))
    chosen, cats = [], set()
    for r in ranked:
        if r["categorie"] in cats:
            continue
        chosen.append(r)
        cats.add(r["categorie"])
        if len(chosen) >= max_pages:
            break
    if len(chosen) < max_pages:
        for r in ranked:
            if r not in chosen:
                chosen.append(r)
                if len(chosen) >= max_pages:
                    break
    return chosen


# ----------------------------------------------------------------------------
# robots.txt et sitemap
# ----------------------------------------------------------------------------

def check_robots(col: Collector, origin: str) -> dict:
    out = {"url": origin + "/robots.txt", "existe": False, "status": None, "disallow_tout": False,
           "sitemaps": [], "erreur": None}
    r = col.get(out["url"], kind="robots")
    out["status"] = r.get("status")
    out["erreur"] = r.get("erreur")
    body = r.get("body_bytes")
    if r.get("status") == 200 and body is not None and b"<html" not in body[:500].lower():
        out["existe"] = True
        txt = body.decode("utf-8", errors="ignore")
        ua_all = False
        for line in txt.splitlines():
            line = line.split("#")[0].strip()
            if not line or ":" not in line:
                continue
            k, v = [x.strip() for x in line.split(":", 1)]
            kl = k.lower()
            if kl == "user-agent":
                ua_all = (v == "*")
            elif kl == "disallow" and ua_all and v == "/":
                out["disallow_tout"] = True
            elif kl == "sitemap" and v:
                out["sitemaps"].append(v)
    return out


def check_sitemap(col: Collector, origin: str, robots: dict) -> dict:
    cands = list(dict.fromkeys(robots.get("sitemaps", []) + [origin + "/sitemap.xml", origin + "/sitemap_index.xml"]))
    out = {"url": None, "existe": False, "status": None, "type": None, "nb_urls": None, "nb_sitemaps": None,
           "testees": [], "erreur": None}
    for u in cands[:3]:
        r = col.get(u, kind="sitemap")
        out["testees"].append({"url": u, "status": r.get("status"), "erreur": r.get("erreur")})
        body = r.get("body_bytes")
        if r.get("status") == 200 and body is not None and b"<" in body[:200]:
            if b"<html" in body[:500].lower():
                continue
            out["url"], out["existe"], out["status"] = u, True, 200
            txt = body.decode("utf-8", errors="ignore")
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", txt, flags=re.I)
            if re.search(r"<sitemapindex", txt, re.I):
                out["type"] = "index"
                out["nb_sitemaps"] = len(locs)
                out["nb_urls"] = None
            else:
                out["type"] = "urlset"
                out["nb_urls"] = len(locs)
            break
        if r.get("erreur") and not out["erreur"]:
            out["erreur"] = r.get("erreur")
    return out


# ----------------------------------------------------------------------------
# Navigateur (Playwright)
# ----------------------------------------------------------------------------

JS_PAGE_METRICS = r"""
() => {
  const vw = window.innerWidth, vh = window.innerHeight;
  const de = document.documentElement, b = document.body;
  const scrollWidth = Math.max(de ? de.scrollWidth : 0, b ? b.scrollWidth : 0);
  const scrollHeight = Math.max(de ? de.scrollHeight : 0, b ? b.scrollHeight : 0);
  const vis = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return null;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) return null;
    return r;
  };
  // boutons d'appel et de contact (liens tel:, boutons/liens « contact », « rdv », « appeler »…, fixes ou non)
  const CONTACT_WORD = /rdv|rendez|contact|(^|[^a-zà-ÿ])appel(er|ez|le|lez)?([^a-zà-ÿ]|$)|t[ée]l[ée]phon|(^|[^a-z])phone|(^|[^a-z0-9])t[ée]l\.?([^a-z0-9]|$)|devis|joindre|rappel/i;
  const CONTACT_HREF = /contact|rendez|rdv|devis|joindre|rappel|prise-de-rendez/i;
  const CONTACT_CLASS = /^(rdv|rendez|rendezvous|contact|contacts|appel|appeler|call|callback|phone|tel|telephone|t[ée]l[ée]phone|devis|rappel|joindre)$/i;
  const isFixed = (el) => {
    let e = el, n = 0;
    while (e && e.nodeType === 1 && n++ < 10) {
      const pos = getComputedStyle(e).position;
      if (pos === 'fixed' || pos === 'sticky') return true;
      e = e.parentElement;
    }
    return false;
  };
  const classTokens = (el) => ((el.getAttribute('class') || '') + ' ' + (el.id || ''))
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2').split(/[^A-Za-z0-9éè]+/).filter(Boolean);
  const found = [];
  const cands = Array.from(document.querySelectorAll('a[href], button, [role="button"]'));
  for (const el of cands) {
    const href = (el.getAttribute('href') || '').trim();
    const hrefLow = href.toLowerCase();
    const txt = (el.innerText || '').replace(/\s+/g, ' ').trim();
    const aria = (el.getAttribute('aria-label') || el.getAttribute('title') || '').replace(/\s+/g, ' ').trim();
    const isTel = hrefLow.startsWith('tel:');
    let motif = null;
    if (isTel) motif = 'lien tel:';
    else if (/^(mailto|sms|whatsapp):/.test(hrefLow) || /wa\.me|api\.whatsapp|m\.me\//.test(hrefLow)) motif = 'lien de messagerie';
    else if (CONTACT_WORD.test(txt)) motif = 'texte';
    else if (CONTACT_WORD.test(aria)) motif = 'aria-label/title';
    else if (/^https?:|^\/|^#|^[a-z0-9]/i.test(hrefLow) && !/^(javascript|data):/.test(hrefLow) && CONTACT_HREF.test(hrefLow)) motif = 'lien vers une page contact';
    else if (classTokens(el).some(t => CONTACT_CLASS.test(t))) motif = 'classe/id';
    if (!motif) continue;
    const r = vis(el);
    if (!r) continue;
    found.push({ texte: (txt || aria).slice(0, 60), href: href.slice(0, 80), tel: isTel, motif,
                 fixe: isFixed(el), classes: classTokens(el).slice(0, 6).join(' ').slice(0, 80),
                 top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left),
                 largeur: Math.round(r.width), hauteur: Math.round(r.height),
                 dans_fold: r.top >= 0 && r.bottom <= vh && r.left >= 0 && r.right <= vw + 1 });
    if (found.length >= 200) break;
  }
  // d'abord ce qui est visible sans défiler, puis les liens tel:, puis par position
  found.sort((a, b) => (b.dans_fold - a.dans_fold) || (b.tel - a.tel) || (a.top - b.top));
  const calls = found.slice(0, 20);
  const bouton_contact = {
    candidats: found.length,
    tel_visible_sans_defiler: found.some(f => f.tel && f.dans_fold),
    contact_visible_sans_defiler: found.some(f => f.dans_fold),
    fixe_visible_sans_defiler: found.some(f => f.fixe && f.dans_fold),
    tel_present: found.some(f => f.tel),
  };
  // plus petit texte
  let minSize = null, minExample = null, smallCount = 0, scanned = 0;
  const all = document.body ? document.body.querySelectorAll('*') : [];
  for (const el of all) {
    if (scanned++ > 4000) break;
    if (['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','SVG','PATH'].includes(el.tagName)) continue;
    let direct = '';
    for (const n of el.childNodes) if (n.nodeType === 3) direct += n.textContent;
    direct = direct.replace(/\s+/g, ' ').trim();
    if (direct.length < 2) continue;
    const r = vis(el);
    if (!r) continue;
    const fs = parseFloat(getComputedStyle(el).fontSize);
    if (!fs) continue;
    if (fs < 12) smallCount++;
    if (minSize === null || fs < minSize) { minSize = fs; minExample = direct.slice(0, 60); }
  }
  const vp = document.querySelector('meta[name="viewport"]');
  return { innerWidth: vw, innerHeight: vh, scrollWidth, scrollHeight,
           debordement: scrollWidth > vw + 1, appels: calls, bouton_contact,
           plus_petit_texte_px: minSize, plus_petit_texte_exemple: minExample,
           textes_moins_12px: smallCount, elements_examines: Math.min(scanned, 4000),
           viewport_meta: vp ? vp.getAttribute('content') : null,
           titre_document: document.title };
}
"""


def run_browser(url: str, out_dir: str) -> dict:
    result = {"outil": "Playwright (Chromium headless)", "date": now_iso(), "url": url,
              "user_agent": USER_AGENT, "vues": {}, "erreur": None}
    if os.path.isdir(DEFAULT_PW_BROWSERS):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", DEFAULT_PW_BROWSERS)
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except Exception as e:  # noqa: BLE001
        result["erreur"] = f"Playwright indisponible : {e}"
        return result
    captures_dir = os.path.join(out_dir, "captures")
    os.makedirs(captures_dir, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            try:
                for vp in VIEWPORTS:
                    view = {"viewport": f"{vp['width']}x{vp['height']}", "status": None, "erreur": None,
                            "networkidle_atteint": None, "temps_chargement_s": None,
                            "requetes": 0, "octets_transferes": 0, "erreurs_console": [],
                            "captures": {}, "metriques": None}
                    ctx = browser.new_context(
                        viewport={"width": vp["width"], "height": vp["height"]},
                        device_scale_factor=vp["scale"], is_mobile=vp["mobile"], has_touch=vp["mobile"],
                        user_agent=USER_AGENT, locale="fr-FR", ignore_https_errors=False,
                    )
                    ctx.set_default_timeout(15_000)
                    page = ctx.new_page()
                    counters = {"req": 0, "bytes": 0}
                    try:
                        cdp = ctx.new_cdp_session(page)
                        cdp.send("Network.enable")
                        cdp.on("Network.requestWillBeSent", lambda e: counters.__setitem__("req", counters["req"] + 1))
                        cdp.on("Network.loadingFinished",
                               lambda e: counters.__setitem__("bytes", counters["bytes"] + int(e.get("encodedDataLength", 0) or 0)))
                    except Exception as e:  # noqa: BLE001
                        view["erreur"] = f"compteur réseau indisponible : {e}"
                    console_errors: list[str] = []
                    page.on("console", lambda m: console_errors.append(m.text[:200]) if m.type == "error" else None)
                    page.on("pageerror", lambda e: console_errors.append(f"JS: {str(e)[:200]}"))
                    t0 = time.time()
                    resp = None
                    try:
                        resp = page.goto(url, wait_until="networkidle", timeout=BROWSER_NAV_TIMEOUT_MS)
                        view["networkidle_atteint"] = True
                        view["temps_chargement_s"] = round(time.time() - t0, 2)
                    except PWTimeout:
                        view["networkidle_atteint"] = False
                        view["temps_chargement_s"] = round(time.time() - t0, 2)
                        view["erreur"] = f"networkidle non atteint en {BROWSER_NAV_TIMEOUT_MS // 1000} s (page analysée en l'état)"
                    except Exception as e:  # noqa: BLE001
                        view["erreur"] = f"navigation impossible : {str(e)[:200]}"
                        result["vues"][vp["nom"]] = view
                        ctx.close()
                        continue
                    if resp is not None:
                        view["status"] = resp.status
                    try:
                        page.wait_for_timeout(800)
                    except Exception:
                        pass
                    try:
                        view["metriques"] = page.evaluate(JS_PAGE_METRICS)
                    except Exception as e:  # noqa: BLE001
                        view["metriques"] = None
                        view["erreur"] = (view["erreur"] or "") + f" | métriques JS impossibles : {str(e)[:120]}"
                    try:
                        f1 = os.path.join(captures_dir, f"{vp['nom']}-{vp['width']}-fold.png")
                        page.screenshot(path=f1, full_page=False, timeout=20_000)
                        view["captures"]["fold"] = os.path.relpath(f1, out_dir)
                    except Exception as e:  # noqa: BLE001
                        view["captures"]["fold_erreur"] = str(e)[:120]
                    try:
                        f2 = os.path.join(captures_dir, f"{vp['nom']}-{vp['width']}-full.png")
                        h = (view["metriques"] or {}).get("scrollHeight") or 0
                        if h and h > MAX_FULLPAGE_HEIGHT:
                            page.screenshot(path=f2, clip={"x": 0, "y": 0, "width": vp["width"], "height": MAX_FULLPAGE_HEIGHT},
                                            full_page=True, timeout=30_000)
                            view["captures"]["full_tronquee_px"] = MAX_FULLPAGE_HEIGHT
                        else:
                            page.screenshot(path=f2, full_page=True, timeout=30_000)
                        view["captures"]["full"] = os.path.relpath(f2, out_dir)
                    except Exception as e:  # noqa: BLE001
                        view["captures"]["full_erreur"] = str(e)[:120]
                    view["requetes"] = counters["req"]
                    view["octets_transferes"] = counters["bytes"]
                    view["erreurs_console"] = console_errors[:15]
                    view["erreurs_console_nombre"] = len(console_errors)
                    result["vues"][vp["nom"]] = view
                    ctx.close()
            finally:
                browser.close()
    except Exception as e:  # noqa: BLE001
        result["erreur"] = f"navigateur : {type(e).__name__} : {str(e)[:200]}"
    return result


# ----------------------------------------------------------------------------
# Lighthouse
# ----------------------------------------------------------------------------

def run_lighthouse(url: str, out_path: str) -> dict:
    res = {"outil": "Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé", "date": now_iso(),
           "url": url, "statut": "non mesuré", "raison": None, "scores": None, "metriques": None, "fichier": None,
           "conditions": "mesure unique depuis un serveur (pas un téléphone réel), réseau et CPU simulés ; "
                         "les valeurs varient d'une mesure à l'autre"}
    if not shutil.which("npx"):
        res["raison"] = "npx introuvable"
        return res
    env = dict(os.environ)
    if "CHROME_PATH" not in env and os.path.exists(DEFAULT_CHROME_PATH):
        env["CHROME_PATH"] = DEFAULT_CHROME_PATH
    cmd = ["npx", "-y", "lighthouse@12", url, "--chrome-flags=--headless=new --no-sandbox --disable-gpu",
           "--form-factor=mobile", "--screenEmulation.mobile", "--throttling-method=simulate",
           "--only-categories=performance,accessibility,best-practices,seo", "--output=json",
           f"--output-path={out_path}", "--quiet"]
    res["commande"] = " ".join(cmd)
    try:
        cp = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=LIGHTHOUSE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        res["raison"] = f"délai dépassé ({LIGHTHOUSE_TIMEOUT_S} s)"
        return res
    except Exception as e:  # noqa: BLE001
        res["raison"] = f"{type(e).__name__} : {str(e)[:160]}"
        return res
    if not os.path.exists(out_path):
        res["raison"] = f"code de sortie {cp.returncode} : {(cp.stderr or cp.stdout)[-300:].strip()}"
        return res
    try:
        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("runtimeError") and data["runtimeError"].get("code") not in (None, "NO_ERROR"):
            res["raison"] = f"erreur Lighthouse : {data['runtimeError'].get('message', '')[:200]}"
            res["fichier"] = os.path.basename(out_path)
            return res
        cats = data.get("categories", {})
        scores = {}
        for k in ("performance", "accessibility", "best-practices", "seo"):
            s = cats.get(k, {}).get("score")
            scores[k] = round(s * 100) if isinstance(s, (int, float)) else None
        aud = data.get("audits", {})

        def nv(k):
            v = aud.get(k, {}).get("numericValue")
            return v if isinstance(v, (int, float)) else None

        lcp, cls, tbt = nv("largest-contentful-paint"), nv("cumulative-layout-shift"), nv("total-blocking-time")
        res["scores"] = scores
        res["metriques"] = {
            "lcp_ms": round(lcp) if lcp is not None else None,
            "cls": round(cls, 3) if cls is not None else None,
            "tbt_ms": round(tbt) if tbt is not None else None,
            "fcp_ms": round(nv("first-contentful-paint")) if nv("first-contentful-paint") is not None else None,
            "speed_index_ms": round(nv("speed-index")) if nv("speed-index") is not None else None,
            "poids_total_octets": round(nv("total-byte-weight")) if nv("total-byte-weight") is not None else None,
        }
        res["statut"] = "mesuré" if scores.get("performance") is not None else "non mesuré"
        res["version"] = data.get("lighthouseVersion")
        res["fichier"] = os.path.basename(out_path)
        res["url_finale"] = data.get("finalDisplayedUrl") or data.get("finalUrl")
    except Exception as e:  # noqa: BLE001
        res["raison"] = f"lecture du rapport impossible : {type(e).__name__}"
    return res


# ----------------------------------------------------------------------------
# Analyse : constats, verdict, points positifs, à préserver
# ----------------------------------------------------------------------------

class Constats:
    def __init__(self):
        self.items: list[dict] = []
        self.non_verifie: list[str] = []

    def add(self, type_, gravite, titre, preuve_url, preuve_valeur, consequence, correction):
        self.items.append({
            "id": f"C{len(self.items) + 1:02d}", "type": type_, "gravite": gravite, "titre": titre,
            "preuve": {"url": preuve_url, "valeur": preuve_valeur},
            "consequence_possible": consequence, "correction": correction,
        })

    def nv(self, msg):
        self.non_verifie.append(msg)


def alt_correction(hints: dict) -> str:
    """Texte de correction pour les images sans alt : exemple fondé sur le métier transmis, sinon consigne générique."""
    metier = (hints.get("metier") or "").strip()
    ville = (hints.get("ville") or "").strip()
    if ville.isupper():          # commune du registre SIRENE en capitales → casse normale
        particules = {"sur", "sous", "en", "le", "la", "les", "de", "du", "des", "lès", "aux", "et"}
        cap = lambda w: w if w in particules else w[:1].upper() + w[1:]   # noqa: E731
        ville = " ".join("-".join(cap(x) for x in w.split("-")) for w in ville.lower().split(" "))
        ville = ville[:1].upper() + ville[1:]
    if metier:
        m = metier[0].upper() + metier[1:]
        ex = f"{m} à {ville} : [ce que montre la photo]" if ville else f"{m} : [ce que montre la photo]"
        return f"Décrire chaque photo en une phrase avec le métier et le lieu (ex. « {ex} »)."
    return "Décrire chaque photo en une phrase : ce qu'elle montre, le métier et le lieu."


def strip_accents(s: str) -> str:
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


def norm_text(s: str) -> str:
    """Minuscules, sans accents, ponctuation et espaces multiples réduits à un espace."""
    s = strip_accents((s or "").lower().replace("’", "'"))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9@.]+", " ", s)).strip()


FORMES_JURIDIQUES = {"sarl", "sas", "sasu", "eurl", "sa", "sci", "snc", "ei", "eirl", "scp", "selarl", "sel", "gie",
                     "societe", "ste", "ets", "etablissements", "entreprise", "groupe", "cie", "compagnie", "et", "fils",
                     "de", "du", "des", "la", "le", "les", "l", "d", "en", "sur", "monsieur", "madame", "m", "mme"}


def chercher_libelle(libelle: str, textes: list[tuple[str, str]]) -> dict | None:
    """Cherche un nom/enseigne dans des textes normalisés : libellé entier, ou tous ses mots significatifs sur une même page."""
    n = norm_text(libelle)
    if not n:
        return None
    tokens = [t for t in n.split() if t not in FORMES_JURIDIQUES and len(t) >= 3]
    for ou, txt in textes:
        if f" {n} " in f" {txt} ":
            return {"valeur": libelle, "ou": ou, "mode": "libellé entier"}
    if tokens:
        for ou, txt in textes:
            hay = f" {txt} "
            if all(f" {t} " in hay or f" {t}s " in hay for t in tokens):
                return {"valeur": libelle, "ou": ou, "mode": "mots significatifs (" + ", ".join(tokens) + ")"}
    return None


def correspondance_entreprise(pages: list[dict], hints: dict) -> dict:
    """Éléments du lead (nom, enseigne, ville, cp, siren) retrouvés dans les pages consultées."""
    textes: list[tuple[str, str]] = []
    for p in pages:
        if not p.get("html"):
            continue
        ou = p.get("final_url") or p.get("url")
        brut = " ".join([p.get("title") or "", p.get("meta_description") or "", " ".join(p.get("h1") or []), p.get("_text") or ""])
        textes.append((ou, norm_text(brut)))
    details: dict[str, dict] = {}
    trouves: list[str] = []
    for cle in ("nom", "enseigne"):
        val = (hints.get(cle) or "").strip()
        if not val:
            details[cle] = {"fourni": False}
            continue
        r = chercher_libelle(val, textes)
        details[cle] = {"fourni": True, "valeur": val, "trouve": bool(r), **({"ou": r["ou"], "mode": r["mode"]} if r else {})}
        if r:
            trouves.append(cle)
    ville = (hints.get("ville") or "").strip()
    if ville:
        nv = norm_text(ville)
        hit = next((ou for ou, txt in textes if f" {nv} " in f" {txt} "), None)
        details["ville"] = {"fourni": True, "valeur": ville, "trouve": bool(hit), **({"ou": hit} if hit else {})}
        if hit:
            trouves.append("ville")
    else:
        details["ville"] = {"fourni": False}
    cp = re.sub(r"\D", "", hints.get("cp") or "")
    if cp:
        hit = next((ou for ou, txt in textes if re.search(rf"(?<!\d){cp}(?!\d)", txt)), None)
        details["cp"] = {"fourni": True, "valeur": cp, "trouve": bool(hit), **({"ou": hit} if hit else {})}
        if hit:
            trouves.append("cp")
    else:
        details["cp"] = {"fourni": False}
    siren = re.sub(r"\D", "", hints.get("siren") or "")
    if siren:
        hit = None
        for ou, txt in textes:
            compact = re.sub(r"(?<=\d)[\s.]+(?=\d)", "", txt)   # « 819 855 206 » → 819855206 (SIRET commence par le SIREN)
            if re.search(rf"(?<!\d){siren}", compact):
                hit = ou
                break
        details["siren"] = {"fourni": True, "valeur": siren, "trouve": bool(hit), **({"ou": hit} if hit else {})}
        if hit:
            trouves.append("siren")
    else:
        details["siren"] = {"fourni": False}
    fournis = [k for k, v in details.items() if v.get("fourni")]
    return {"elements_trouves": trouves, "elements_fournis": fournis,
            "elements_non_trouves": [k for k in fournis if k not in trouves], "details": details,
            "note": "Recherche sur les pages consultées (titre, description, H1, texte visible), sans accents ni casse ; "
                    "nom et enseigne acceptés si le libellé entier ou tous ses mots significatifs figurent sur une même page."}


def analyse(audit: dict, hints: dict) -> dict:
    c = Constats()
    positifs: list[str] = []
    pages = audit["pages"]
    home = pages[0] if pages else None
    home_url = audit["cible"]["url_finale"] or audit["cible"]["url_demandee"]
    home_ok = bool(home and home.get("html") and (home.get("status") or 0) < 400)
    http = audit["http"]
    year_now = dt.datetime.now().year

    # --- HTTPS / redirections ---
    final_scheme = urlparse(home_url).scheme if home_url else None
    if home_ok and final_scheme != "https":
        th = http.get("test_https") or {}
        if th.get("status") and th["status"] < 400 and not th.get("erreur"):
            c.add("fait observé", "haute", "Redirection http→https absente (HTTPS disponible mais non forcé)", home_url,
                  f"URL finale en http (réponse {audit['cible'].get('status')}) alors que {th['url']} répond {th['status']}",
                  "Le visiteur qui arrive sans « https » peut voir « Non sécurisé » ; deux versions du site risquent de coexister pour Google.",
                  "Rediriger (301) tout le trafic http:// vers https:// et déclarer la version https dans la Search Console.")
        else:
            detail = f"URL finale en {final_scheme}"
            if th:
                detail += f" ; {th.get('url')} : {th.get('erreur') or ('status ' + str(th.get('status')))}"
            c.add("fait observé", "haute", "Site servi sans HTTPS", home_url, detail,
                  "Le navigateur peut afficher « Non sécurisé » à côté de l'adresse ; une partie des visiteurs risque de renoncer, et Google favorise les pages HTTPS.",
                  "Installer un certificat TLS (Let's Encrypt est gratuit chez la plupart des hébergeurs) et rediriger tout le site en HTTPS.")
    elif home_ok:
        t = http.get("test_http")
        if t and t.get("erreur"):
            c.nv(f"redirection http→https non vérifiée ({t['erreur']})")
        elif t and t.get("final_url") and urlparse(t["final_url"]).scheme == "https":
            positifs.append("HTTPS actif et redirection http→https en place")
        elif t and t.get("status") and t.get("final_url") and urlparse(t["final_url"]).scheme == "http":
            c.add("fait observé", "haute", "Redirection http→https absente", t["url"],
                  f"réponse {t['status']} servie en http sans redirection (URL finale {t['final_url']})",
                  "Un visiteur qui tape l'adresse sans « https » ou suit un vieux lien peut rester sur la version non sécurisée, avec l'avertissement du navigateur et un contenu dupliqué pour Google.",
                  "Ajouter une redirection 301 de http:// vers https:// sur l'hébergement (fichier .htaccess ou réglage du panneau d'hébergement).")
        hsts = http.get("hsts")
        if hsts:
            positifs.append("En-tête HSTS présent (le navigateur force HTTPS après la première visite)")
        w = http.get("test_www")
        if w and not w.get("erreur") and w.get("final_url") and w.get("status") and w["status"] < 400:
            if normalize_url(w["final_url"]) != normalize_url(home_url) and same_site(w["final_url"], home_url) and host_base(urlparse(w["final_url"]).netloc) == host_base(urlparse(home_url).netloc) and urlparse(w["final_url"]).netloc != urlparse(home_url).netloc:
                c.add("fait observé", "basse", "Versions avec et sans « www » servies toutes deux", w["url"],
                      f"réponse {w['status']} sur {w['final_url']} sans redirection vers {home_url}",
                      "Deux adresses pour le même contenu : Google peut hésiter sur la version à afficher.",
                      "Rediriger (301) l'une des deux versions vers l'autre.")
            else:
                positifs.append("Variante www / sans www redirigée correctement")
        elif w and w.get("erreur"):
            c.nv(f"variante www non vérifiée ({w['erreur']})")

    # --- page inaccessible ---
    if not home_ok:
        c.add("fait observé", "haute", "Page d'accueil non chargée", home_url or audit["cible"]["url_demandee"],
              f"status {home.get('status') if home else None}, erreur : {home.get('erreur') if home else 'aucune réponse'}",
              "Le site est injoignable ou renvoie une erreur : les clients risquent de ne pas pouvoir le consulter.",
              "Vérifier l'hébergement, le nom de domaine et le certificat ; relancer l'audit ensuite.")

    # --- navigateur mobile ---
    br = audit.get("navigateur") or {}
    mob = (br.get("vues") or {}).get("mobile") or {}
    mm = mob.get("metriques") or {}
    if home_ok:
        vp_meta = (home.get("meta_viewport") or mm.get("viewport_meta"))
        if not vp_meta:
            c.add("fait observé", "haute", "Balise meta viewport absente", home_url, "aucune balise <meta name=\"viewport\">",
                  "Sur téléphone, la page risque de s'afficher en version réduite : textes minuscules, zoom nécessaire pour lire ou cliquer.",
                  "Ajouter <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> et vérifier la mise en page à 375 px.")
        else:
            positifs.append("Balise viewport présente")
    if mm:
        if mm.get("debordement"):
            c.add("mesure", "haute", "Débordement horizontal à 375 px", home_url,
                  f"largeur défilable {mm['scrollWidth']} px pour un écran de {mm['innerWidth']} px (Playwright, {br.get('date')})",
                  "Sur téléphone, une partie du contenu sort de l'écran ; textes et boutons peuvent être coupés, et il faut défiler sur le côté.",
                  "Corriger les éléments plus larges que l'écran (images, tableaux, blocs à largeur fixe) avec max-width:100 % et une mise en page fluide.")
        else:
            positifs.append("Aucun débordement horizontal à 375 px")
        appels_fold = [a for a in mm.get("appels", []) if a.get("tel") and a.get("dans_fold")]
        if appels_fold:
            positifs.append(f"Bouton d'appel (tel:) visible sans défiler à 375 px (« {appels_fold[0]['texte'] or appels_fold[0]['href']} »)")
        pst = mm.get("plus_petit_texte_px")
        if pst is not None and pst < 12 and (mm.get("textes_moins_12px") or 0) >= 3:
            c.add("mesure", "basse", "Textes très petits sur mobile", home_url,
                  f"plus petit texte {pst} px (ex. « {mm.get('plus_petit_texte_exemple')} »), {mm.get('textes_moins_12px')} éléments sous 12 px à 375 px",
                  "Ces textes peuvent être difficiles à lire sans zoomer, en particulier les coordonnées et les mentions pratiques.",
                  "Utiliser une taille de texte d'au moins 14 à 16 px pour le contenu et 12 px minimum pour les mentions secondaires.")
        if mob.get("erreurs_console_nombre"):
            c.add("mesure", "basse", "Erreurs JavaScript ou ressources en échec au chargement", home_url,
                  f"{mob['erreurs_console_nombre']} erreur(s) console à 375 px, ex. : {mob['erreurs_console'][0] if mob.get('erreurs_console') else ''}",
                  "Des fonctions (menu, formulaire, carrousel) peuvent ne pas marcher chez certains visiteurs.",
                  "Corriger ou retirer les scripts en erreur ; vérifier les ressources en erreur (4xx).")
        else:
            positifs.append("Aucune erreur console au chargement mobile")
        octets = mob.get("octets_transferes") or 0
        if octets > 3_000_000:
            c.add("mesure", "moyenne", "Page d'accueil lourde sur mobile", home_url,
                  f"{octets / 1_000_000:.1f} Mo transférés, {mob.get('requetes')} requêtes (Playwright, {br.get('date')})",
                  "Le chargement risque d'être long en 4G ou en zone mal couverte ; une partie des visiteurs peut partir avant l'affichage.",
                  "Compresser et redimensionner les images (WebP), supprimer les scripts inutiles, activer la mise en cache.")
    elif home_ok:
        c.nv("affichage mobile non vérifié (navigateur indisponible : %s)" % (br.get("erreur") or mob.get("erreur") or "pas de mesure"))

    # --- Lighthouse ---
    lh = audit.get("lighthouse") or {}
    if lh.get("statut") == "mesuré" and lh.get("scores", {}).get("performance") is not None:
        perf = lh["scores"]["performance"]
        met = lh.get("metriques") or {}
        detail = f"performance {perf}/100, LCP {met.get('lcp_ms')} ms, CLS {met.get('cls')}, TBT {met.get('tbt_ms')} ms ({lh['outil']}, {lh['date']})"
        if perf < 50:
            c.add("mesure", "haute", "Performance mobile faible (Lighthouse)", home_url, detail,
                  "La page s'affiche lentement sur téléphone ; des visiteurs venus de Google Maps risquent de repartir avant d'avoir vu le numéro.",
                  "Réduire le poids des images, limiter les scripts et polices, servir le site depuis un hébergement rapide avec cache.")
        elif perf < 80:
            c.add("mesure", "moyenne", "Performance mobile moyenne (Lighthouse)", home_url, detail,
                  "L'affichage peut être perceptiblement lent sur un réseau mobile ordinaire.",
                  "Optimiser images et scripts ; viser un LCP sous 2,5 s.")
        else:
            positifs.append(f"Performance mobile Lighthouse {perf}/100 (LCP {met.get('lcp_ms')} ms)")
        for k, label in (("accessibility", "accessibilité"), ("seo", "SEO technique"), ("best-practices", "bonnes pratiques")):
            s = lh["scores"].get(k)
            if s is not None and s >= 90:
                positifs.append(f"Lighthouse {label} {s}/100")
            elif s is not None and s < 70:
                c.add("mesure", "basse", f"Score Lighthouse {label} bas", home_url, f"{label} {s}/100 ({lh['date']})",
                      "Indice de défauts techniques (contrastes, libellés, balises) que Lighthouse détaille dans lighthouse.json.",
                      "Consulter les audits détaillés et corriger les points listés.")
    else:
        c.nv(f"performance Lighthouse non mesurée ({lh.get('raison') or 'non lancé'})")

    # --- balises ---
    if home_ok:
        titles = [p.get("title") for p in pages if p.get("html") and p.get("title")]
        dup = [t for t, n in Counter(titles).items() if n > 1]
        if not home.get("title"):
            c.add("fait observé", "moyenne", "Balise <title> absente sur l'accueil", home_url, "aucun <title>",
                  "Google peut afficher un titre improvisé ; le métier et la ville risquent de ne pas apparaître dans les résultats.",
                  "Rédiger un titre de 50 à 60 caractères : métier + ville + nom de l'entreprise.")
        elif home["title_longueur"] > 65:
            c.add("fait observé", "moyenne", "Titre de l'accueil trop long", home_url,
                  f"{home['title_longueur']} caractères : « {home['title'][:90]} »",
                  "Le titre peut être coupé dans les résultats Google.",
                  "Ramener le titre à 50–60 caractères en gardant métier et ville au début.")
        else:
            positifs.append(f"Titre présent ({home['title_longueur']} caractères)")
        if dup:
            c.add("fait observé", "moyenne", "Même titre sur plusieurs pages", home_url,
                  f"« {dup[0][:80]} » sur {Counter(titles)[dup[0]]} pages consultées",
                  "Google peut ne pas distinguer les pages ; les pages services/contact risquent de perdre leur chance d'apparaître.",
                  "Donner à chaque page un titre propre (service + ville).")
        if not home.get("meta_description"):
            c.add("fait observé", "moyenne", "Meta description absente sur l'accueil", home_url, "aucune <meta name=\"description\">",
                  "Google compose lui-même l'extrait ; l'accroche (zone, devis gratuit, urgence) peut manquer.",
                  "Rédiger une description de 120 à 155 caractères avec métier, zone et appel à l'action.")
        elif home["meta_description_longueur"] > 165:
            c.add("fait observé", "basse", "Meta description trop longue", home_url, f"{home['meta_description_longueur']} caractères",
                  "L'extrait peut être tronqué dans les résultats.", "Ramener à 120–155 caractères.")
        else:
            positifs.append(f"Meta description présente ({home['meta_description_longueur']} caractères)")
        if home.get("meta_robots") and re.search(r"noindex", home["meta_robots"], re.I):
            c.add("fait observé", "haute", "Accueil marqué noindex", home_url, f"meta robots « {home['meta_robots']} »",
                  "La page d'accueil risque d'être exclue de Google.", "Retirer « noindex » de la balise meta robots.")
        if audit["robots"].get("disallow_tout"):
            c.add("fait observé", "haute", "robots.txt interdit tout le site aux moteurs", audit["robots"]["url"], "Disallow: / pour User-agent: *",
                  "Google risque de ne pas pouvoir explorer le site.", "Retirer la règle Disallow: / du robots.txt.")
        if home.get("canonical"):
            if not same_site(home["canonical"], home_url):
                c.add("fait observé", "moyenne", "Canonical pointant vers un autre domaine", home_url, home["canonical"],
                      "Google peut attribuer la page à un autre site.", "Faire pointer la balise canonical vers l'URL de la page elle-même.")
        if home["h1_nombre"] == 0:
            c.add("fait observé", "basse", "Aucun titre H1 sur l'accueil", home_url, "0 balise <h1>",
                  "Le message principal (métier + ville) peut ne pas être identifié comme titre par les moteurs et les lecteurs d'écran.",
                  "Ajouter un H1 unique en haut de page : métier, ville, promesse.")
        elif home["h1_nombre"] > 1:
            c.add("fait observé", "basse", "Plusieurs titres H1 sur l'accueil", home_url, f"{home['h1_nombre']} balises <h1>",
                  "La hiérarchie des titres peut en être brouillée.", "Garder un seul H1, passer les autres en H2.")
        else:
            positifs.append(f"H1 unique : « {home['h1'][0][:70]} »")
        if not home.get("lang"):
            c.add("fait observé", "basse", "Attribut lang absent sur <html>", home_url, "pas d'attribut lang",
                  "Lecteurs d'écran et traducteurs automatiques doivent deviner la langue.", "Ajouter <html lang=\"fr\">.")
        sa_pages = [(p["final_url"] or p["url"], p["images_sans_alt"], p["images_total"]) for p in pages if p.get("html") and p.get("images_sans_alt")]
        if sa_pages:
            tot = sum(x[1] for x in sa_pages)
            c.add("fait observé", "basse", "Images sans attribut alt", sa_pages[0][0],
                  f"{tot} image(s) sans alt sur {len(sa_pages)} page(s) consultée(s) (accueil : {home['images_sans_alt']}/{home['images_total']})",
                  "Ces photos risquent de ne pas remonter dans Google Images et restent muettes pour les lecteurs d'écran.",
                  alt_correction(hints))
        elif home.get("images_total"):
            positifs.append(f"Toutes les images de l'accueil ont un attribut alt ({home['images_total']} images)")
        tel_any = [p for p in pages if p.get("html") and p.get("liens_tel")]
        # Bouton d'appel / de contact sur le premier écran mobile : trois cas distingués (navigateur requis)
        appels = (mm.get("appels") or []) if mm else []
        tel_fold = [a for a in appels if a.get("tel") and a.get("dans_fold")]
        contact_fold = [a for a in appels if a.get("dans_fold") and not a.get("tel")]
        if not tel_any:
            phones = home.get("telephones_detectes") or []
            preuve = ("numéro affiché en texte : " + ", ".join(phones)) if phones else "aucun lien tel: ni numéro détecté sur les pages consultées"
            if mm and not contact_fold:
                preuve += " ; aucun bouton de contact visible sans défiler à 375 px"
            c.add("fait observé", "moyenne", "Aucun numéro de téléphone cliquable (lien tel:)", home_url, preuve,
                  "Sur téléphone, le visiteur doit recopier le numéro ; une partie risque d'abandonner.",
                  "Transformer le numéro en lien <a href=\"tel:+33…\"> et le placer en haut de page.")
        else:
            positifs.append(f"Numéro cliquable (tel:) présent : {tel_any[0]['liens_tel'][0]}")
        if mm and not tel_fold:
            if contact_fold:
                b = contact_fold[0]
                libelle = b.get("texte") or b.get("href") or b.get("classes") or "sans libellé"
                c.add("mesure", "basse", "Bouton de contact visible sans défiler à 375 px, mais sans lien d'appel direct", home_url,
                      f"bouton « {libelle} »{' (fixe à l’écran)' if b.get('fixe') else ''} visible sur le premier écran mobile, repéré par {b.get('motif') or 'son libellé'} ; "
                      f"{_ou_tel(tel_any, home_url)} (Playwright, {br.get('date')})",
                      "Le visiteur pressé peut avoir à passer par une page ou un formulaire avant de pouvoir appeler.",
                      "Donner à ce bouton (ou à un bouton voisin) un lien d'appel direct <a href=\"tel:+33…\"> pour appeler en un appui.")
            elif tel_any:
                c.add("mesure", "moyenne", "Aucun bouton de contact visible sans défiler à 375 px", home_url,
                      f"{_ou_tel(tel_any, home_url)}, mais aucun lien d'appel ni bouton de contact sur le premier écran mobile (Playwright, {br.get('date')})",
                      "Le visiteur pressé risque de ne pas voir comment appeler sans défiler.",
                      "Placer un bouton « Appeler » dans l'en-tête ou une barre fixe en bas d'écran sur mobile.")
        ville_ok, ville_preuve = False, None
        if hints.get("ville") and re.search(rf"(?<!\w){re.escape(hints['ville'])}(?!\w)", home.get("_text", ""), re.I):
            ville_ok, ville_preuve = True, f"ville « {hints['ville']} » trouvée sur l'accueil"
        elif hints.get("cp") and hints["cp"] in home.get("_text", ""):
            ville_ok, ville_preuve = True, f"code postal {hints['cp']} trouvé sur l'accueil"
        elif home.get("adresses_detectees"):
            a = home["adresses_detectees"][0]
            ville_ok, ville_preuve = True, f"adresse détectée : {a['code_postal']} {a['ville']}"
        elif home.get("departements_mentionnes"):
            ville_ok, ville_preuve = True, f"zone mentionnée : {', '.join(home['departements_mentionnes'])}"
        elif home.get("mention_zone"):
            ville_ok, ville_preuve = True, "formulation de zone d'intervention détectée"
        if ville_ok:
            positifs.append(f"Ville ou zone d'intervention visible sur l'accueil ({ville_preuve})")
        else:
            c.add("fait observé", "moyenne", "Aucune ville ni zone d'intervention repérée sur l'accueil", home_url,
                  "aucun code postal + ville, département ou formule de zone détecté (heuristique ; à confirmer à l'œil)",
                  "Le visiteur peut ne pas savoir si l'entreprise intervient chez lui ; Google risque de ne pas relier le site à la zone.",
                  "Écrire la ville et le rayon d'intervention dans le titre, le H1 et le pied de page.")
        if home.get("jsonld_localbusiness"):
            lb = [t for t in home["jsonld_types"] if t in LOCALBUSINESS_TYPES or t.endswith(("Business", "Store", "Salon", "Contractor", "Shop"))]
            positifs.append(f"Données structurées LocalBusiness présentes ({', '.join(lb[:4])})")
        else:
            c.add("fait observé", "basse", "Données structurées LocalBusiness absentes", home_url,
                  f"types JSON-LD trouvés : {', '.join(home['jsonld_types']) or 'aucun'}",
                  "Google doit deviner nom, adresse, téléphone et horaires au lieu de les lire ; ils peuvent manquer dans les résultats.",
                  "Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google.")
        if not home.get("mention_devis"):
            c.add("fait observé", "basse", "Aucune mention « devis » sur l'accueil", home_url, "mot « devis » absent du texte de l'accueil",
                  "Le visiteur peut ne pas voir comment demander un chiffrage.", "Ajouter un bouton « Demander un devis » visible.")
        cy = home.get("copyright_annee")
        if cy and cy < year_now - 1:
            c.add("fait observé", "basse", "Année de copyright ancienne (indice de site non mis à jour)", home_url,
                  f"© {cy} (année courante {year_now})",
                  "Le visiteur peut croire que l'entreprise n'est plus active.", "Mettre l'année à jour automatiquement ou la retirer.")
        elif cy:
            positifs.append(f"Copyright à jour (© {cy})")
        gen = home.get("generateur") or {}
        if gen.get("generateur_gratuit"):
            noms = ", ".join(g["nom"] for g in gen["detectes"])
            c.add("fait observé", "basse", "Site construit avec un générateur grand public (information)", home_url, noms,
                  "Les marges de manœuvre peuvent être limitées sur la vitesse, le référencement et le nom de domaine ; dépendance à l'éditeur.",
                  "Information pour l'échange : la refonte peut reprendre textes et photos sur un hébergement dédié.")
        broken = [p for p in pages[1:] if p.get("status") and p["status"] >= 400]
        if broken:
            c.add("fait observé", "moyenne", "Lien de navigation vers une page en erreur", broken[0]["url"],
                  f"status {broken[0]['status']} ({len(broken)} lien(s) concerné(s))",
                  "Le visiteur peut tomber sur une page d'erreur depuis le menu.", "Corriger ou retirer les liens cassés.")
        if audit["sitemap"].get("existe"):
            positifs.append(f"Sitemap présent ({audit['sitemap']['url']}, {audit['sitemap'].get('nb_urls') if audit['sitemap'].get('nb_urls') is not None else str(audit['sitemap'].get('nb_sitemaps')) + ' sous-sitemaps'} URL)")
        if audit["robots"].get("existe") and not audit["robots"].get("disallow_tout"):
            positifs.append("robots.txt présent et non bloquant")

    # --- verdict ---
    g = Counter(x["gravite"] for x in c.items)
    if not home_ok:
        verdict, motif = "informations insuffisantes", "la page d'accueil n'a pas pu être chargée"
    elif len(c.items) < 3:
        verdict, motif = "informations insuffisantes", f"moins de 3 constats fiables ({len(c.items)})"
    elif g["haute"] >= 2 or (g["haute"] == 1 and g["moyenne"] >= 2):
        verdict, motif = "refonte pertinente", f"{g['haute']} constat(s) de gravité haute et {g['moyenne']} moyenne(s)"
    elif g["haute"] == 0 and g["moyenne"] >= 2:
        verdict, motif = "amélioration ciblée préférable", f"{g['moyenne']} constats moyens, aucun haut"
    else:
        verdict, motif = "aucune amélioration substantielle établie", f"{g['haute']} haute, {g['moyenne']} moyenne(s), {g['basse']} basse(s)"

    # --- à préserver ---
    pages_trouvees = [{"url": p.get("final_url") or p["url"], "role": p["role"], "title": p.get("title"), "status": p.get("status")}
                      for p in pages if p.get("status")]
    phones, emails, adresses = [], [], []
    for p in pages:  # d'abord les numéros des liens tel: (fiables), ensuite ceux détectés par regex dans le texte
        for lt in p.get("liens_tel", []) or []:
            ph = normalize_phone(lt)
            if ph and ph not in phones and PHONE_RE.search(ph):
                phones.append(ph)
    for p in pages:
        for ph in p.get("telephones_detectes", []) or []:
            if ph not in phones:
                phones.append(ph)
        for em in p.get("emails_detectes", []) or []:
            if em not in emails:
                emails.append(em)
        for ad in p.get("adresses_detectees", []) or []:
            if ad not in adresses:
                adresses.append(ad)
    services = services_listes(pages)
    nav = []
    if home:
        for l in home.get("_nav_links", []):
            if l["texte"] and l["texte"] not in nav:
                nav.append(l["texte"])
    a_preserver = {
        "pages_trouvees": pages_trouvees,
        "menu": nav[:15],
        "coordonnees": {"telephones": phones[:5], "emails": emails[:5], "adresses": adresses[:3]},
        "services_listes": services,
        "note": "Inventaire limité aux pages consultées ; les intitulés de services sont les listes de prestations (ul/li) et les titres H2/H3 "
                "relevés hors formulaire sur les pages accueil/services (12 au plus), à vérifier avec le client.",
    }
    return {"constats": c.items, "non_verifie": c.non_verifie, "verdict": verdict, "verdict_motif": motif,
            "gravites": {"haute": g["haute"], "moyenne": g["moyenne"], "basse": g["basse"]},
            "ce_qui_fonctionne": positifs, "a_preserver": a_preserver,
            "correspondance_entreprise": correspondance_entreprise(pages, hints)}


def services_listes(pages: list[dict]) -> list[str]:
    """Prestations probables : listes ul/li sous un titre « prestations/services… », puis titres H2/H3 hors formulaire
    des pages services puis accueil (pages actualités/recrutement/mentions exclues) ; 12 entrées dédoublonnées au plus."""
    services: list[str] = []
    seen: set[str] = set()

    def push(t: str | None) -> None:
        if t and len(services) < MAX_SERVICES:
            k = norm_text(t)
            if k and k not in seen:
                seen.add(k)
                services.append(t)

    def page_ok(p: dict) -> bool:
        if not p.get("html") or p.get("role") not in ("services", "accueil"):
            return False
        hay = " ".join([p.get("final_url") or p.get("url") or "", p.get("title") or ""])
        return not NON_SERVICE_PAGE_RE.search(hay)

    candidates = [p for p in pages if page_ok(p)]
    for p in candidates:                       # 1. listes de prestations (les plus fiables)
        for lst in p.get("_listes_prestations") or []:
            for t in lst.get("elements") or []:
                push(clean_service_title(t))
    for role in ("services", "accueil"):       # 2. titres H2/H3 hors formulaire, pages services d'abord
        for p in candidates:
            if p.get("role") != role:
                continue
            titres = p.get("_titres_hors_formulaire")
            if titres is None:                 # audit.json ancien ou page sans la clé privée : repli sur h2/h3
                titres = (p.get("h2") or []) + (p.get("h3") or [])
            for h in titres:
                push(clean_service_title(h))
    return services[:MAX_SERVICES]


# ----------------------------------------------------------------------------
# Rapport Markdown
# ----------------------------------------------------------------------------

def fmt_bytes(n):
    if n is None:
        return "non mesuré"
    return f"{n / 1_000_000:.2f} Mo" if n >= 1_000_000 else f"{n / 1000:.0f} Ko"


def write_markdown(audit: dict, path: str) -> None:
    an = audit["analyse"]
    cible = audit["cible"]
    url = cible["url_finale"] or cible["url_demandee"]
    pages = audit["pages"]
    home = pages[0] if pages else {}
    lh = audit.get("lighthouse") or {}
    br = audit.get("navigateur") or {}
    mob = (br.get("vues") or {}).get("mobile") or {}
    dsk = (br.get("vues") or {}).get("desktop") or {}
    mm = mob.get("metriques") or {}
    g = an["gravites"]
    L = []
    L.append(f"# Audit du site {urlparse(url).netloc}")
    L.append("")
    L.append(f"URL auditée : {url} · Domaine demandé : {cible.get('domaine_demande') or urlparse(cible['url_demandee']).netloc} · Domaine final : {cible.get('domaine_final') or 'non établi'} · Date : {audit['meta']['date']} · Outil : audit_site.py (requests + Playwright + Lighthouse 12), lecture seule, User-Agent « {USER_AGENT} ».")
    L.append("")
    # Synthèse (5 lignes max)
    L.append("## Synthèse")
    L.append("")
    syn = []
    syn.append(f"**Verdict : {an['verdict']}** ({an['verdict_motif']}).")
    syn.append(f"{len(an['constats'])} constats : {g['haute']} de gravité haute, {g['moyenne']} moyenne, {g['basse']} basse ; {len(pages)} page(s) consultée(s).")
    if lh.get("statut") == "mesuré":
        s = lh["scores"]
        m = lh["metriques"]
        syn.append(f"Lighthouse mobile ({lh['date']}) : performance {s['performance']}/100, accessibilité {s['accessibility']}, bonnes pratiques {s['best-practices']}, SEO {s['seo']} ; LCP {m['lcp_ms']} ms, CLS {m['cls']}, TBT {m['tbt_ms']} ms.")
    else:
        syn.append(f"Lighthouse : non mesuré ({lh.get('raison') or 'non lancé'}).")
    if mm:
        syn.append(f"Mobile 375 px (Playwright) : {'débordement horizontal' if mm.get('debordement') else 'pas de débordement'}, {mob.get('requetes')} requêtes, {fmt_bytes(mob.get('octets_transferes'))}, {mob.get('temps_chargement_s')} s jusqu'à networkidle{'' if mob.get('networkidle_atteint') else ' (non atteint)'}.")
    else:
        syn.append(f"Mobile : non vérifié ({br.get('erreur') or mob.get('erreur') or 'navigateur non lancé'}).")
    hautes = [c["titre"] for c in an["constats"] if c["gravite"] == "haute"]
    if hautes:
        syn.append("Points bloquants : " + " ; ".join(hautes) + ".")
    L.extend(syn[:5])
    L.append("")
    L.append("## Ce qui fonctionne")
    L.append("")
    if an["ce_qui_fonctionne"]:
        L.extend(f"- {x}" for x in an["ce_qui_fonctionne"])
    else:
        L.append("- Rien n'a pu être établi (page non chargée ou mesures indisponibles).")
    L.append("")
    L.append("## Actions prioritaires")
    L.append("")
    order = {"haute": 0, "moyenne": 1, "basse": 2}
    cs = sorted(an["constats"], key=lambda x: (order[x["gravite"]], x["id"]))
    for i, cst in enumerate(cs[:8], 1):
        L.append(f"{i}. **{cst['titre']}** ({cst['gravite']}) : {cst['correction']}")
    if not cs:
        L.append("Aucune action établie.")
    L.append("")
    L.append("## Constats détaillés")
    L.append("")
    L.append("| Priorité | Problème | Preuve | Conséquence possible | Correction |")
    L.append("|---|---|---|---|---|")
    for cst in cs:
        pv = f"{cst['preuve']['url']} — {cst['preuve']['valeur']}".replace("|", "\\|")
        L.append(f"| {cst['gravite']} | {cst['titre']} ({cst['type']}) | {pv} | {cst['consequence_possible']} | {cst['correction']} |")
    if not cs:
        L.append("| — | aucun constat | — | — | — |")
    L.append("")
    if an["non_verifie"]:
        L.append("Non vérifié / non mesuré : " + " ; ".join(an["non_verifie"]) + ".")
        L.append("")
    L.append("## Mesures et conditions")
    L.append("")
    http = audit["http"]
    L.append(f"- HTTP (requests, {audit['meta']['date']}) : URL demandée {cible['url_demandee']} → finale {url} ; chaîne : {' → '.join(f'{h['status']} {h['url']}' for h in cible.get('chaine', [])) or 'aucune redirection'} ; HSTS : {http.get('hsts') or 'absent'}.")
    t = http.get("test_http")
    if t:
        L.append(f"- Test http:// : {t['url']} → {t.get('final_url') or 'aucune réponse'} (status {t.get('status')}{', erreur : ' + t['erreur'] if t.get('erreur') else ''}).")
    th = http.get("test_https")
    if th:
        L.append(f"- Test https:// : {th['url']} → {th.get('final_url') or 'aucune réponse'} (status {th.get('status')}{', erreur : ' + th['erreur'] if th.get('erreur') else ''}).")
    w = http.get("test_www")
    if w:
        L.append(f"- Test variante www : {w['url']} → {w.get('final_url') or 'aucune réponse'} (status {w.get('status')}{', erreur : ' + w['erreur'] if w.get('erreur') else ''}).")
    rb = audit["robots"]
    L.append(f"- robots.txt : {'présent' if rb.get('existe') else 'absent ou non lisible'} (status {rb.get('status')}{', erreur : ' + rb['erreur'] if rb.get('erreur') else ''}){' ; Disallow: / !' if rb.get('disallow_tout') else ''}.")
    sm = audit["sitemap"]
    if sm.get("existe"):
        L.append(f"- sitemap : {sm['url']} ({sm['type']}, {sm.get('nb_urls') if sm.get('nb_urls') is not None else str(sm.get('nb_sitemaps')) + ' sous-sitemaps'} URL ; sans exploration exhaustive).")
    else:
        L.append(f"- sitemap : aucun trouvé parmi {', '.join(x['url'] for x in sm.get('testees', []))}.")
    if br.get("vues"):
        for nom, v in br["vues"].items():
            m = v.get("metriques") or {}
            L.append(f"- Navigateur {nom} {v['viewport']} (Playwright Chromium, {br['date']}) : status {v.get('status')}, {v.get('temps_chargement_s')} s jusqu'à networkidle{'' if v.get('networkidle_atteint') else ' (non atteint)'}, {v.get('requetes')} requêtes, {fmt_bytes(v.get('octets_transferes'))}, {v.get('erreurs_console_nombre', 0)} erreur(s) console, largeur défilable {m.get('scrollWidth', 'non mesurée')} px, plus petit texte {m.get('plus_petit_texte_px', 'non mesuré')} px{'; ' + v['erreur'] if v.get('erreur') else ''}.")
            caps = [c for k, c in (v.get("captures") or {}).items() if k in ("fold", "full")]
            if caps:
                L.append(f"  Captures : {', '.join(caps)}.")
    else:
        L.append(f"- Navigateur : non lancé ou en échec ({br.get('erreur') or 'désactivé'}).")
    if lh.get("statut") == "mesuré":
        L.append(f"- Lighthouse : {lh['outil']}, {lh['date']}, URL {lh.get('url_finale') or lh['url']} ; {lh['conditions']} ; rapport : {lh.get('fichier')}.")
    else:
        L.append(f"- Lighthouse : non mesuré ({lh.get('raison') or 'non lancé'}).")
    L.append("")
    L.append("## Pages consultées")
    L.append("")
    L.append("| Rôle | URL | Status | Title (longueur) | Description (longueur) | H1 | tel: | Images sans alt |")
    L.append("|---|---|---|---|---|---|---|---|")
    for p in pages:
        if p.get("html"):
            L.append(f"| {p['role']} | {p.get('final_url') or p['url']} | {p.get('status')} | {(p.get('title') or '—')[:60].replace('|', '/')} ({p.get('title_longueur')}) | {p.get('meta_description_longueur')} | {p.get('h1_nombre')} | {len(p.get('liens_tel') or [])} | {p.get('images_sans_alt')}/{p.get('images_total')} |")
        else:
            L.append(f"| {p['role']} | {p['url']} | {p.get('status')} | non analysée ({p.get('erreur') or 'contenu non HTML'}) | | | | |")
    L.append("")
    L.append("## Risques de refonte et éléments à préserver")
    L.append("")
    ap = an["a_preserver"]
    L.append(f"Inventaire limité aux {len(pages)} page(s) consultée(s) ; le site peut en compter davantage (sitemap : {sm.get('nb_urls') if sm.get('nb_urls') is not None else 'nombre inconnu'}). Toute page non listée ici doit être inventoriée avant mise en ligne, et chaque ancienne adresse redirigée (301).")
    L.append("")
    L.append("- Pages trouvées : " + ("; ".join(f"{p['role']} → {p['url']} ({p['status']})" for p in ap["pages_trouvees"]) or "aucune"))
    L.append("- Menu : " + (", ".join(ap["menu"]) or "aucun lien de navigation repéré"))
    co = ap["coordonnees"]
    L.append(f"- Coordonnées relevées : téléphones {', '.join(co['telephones']) or 'aucun'} ; e-mails {', '.join(co['emails']) or 'aucun'} ; adresses {'; '.join(((a['rue'] + ', ') if a['rue'] else '') + a['code_postal'] + ' ' + a['ville'] for a in co['adresses']) or 'aucune détectée'}.")
    L.append("- Services listés (listes de prestations et titres H2/H3, à vérifier) : " + (", ".join(ap["services_listes"]) or "aucun relevé"))
    corr = an.get("correspondance_entreprise") or {}
    if corr.get("elements_fournis"):
        det = corr.get("details") or {}
        trouves = [f"{k} (« {det[k].get('valeur')} », {det[k].get('ou')})" for k in corr.get("elements_trouves", [])]
        L.append("- Correspondance avec le lead : " + ("retrouvés : " + " ; ".join(trouves) if trouves else "aucun élément du lead retrouvé")
                 + (" ; non retrouvés : " + ", ".join(f"{k} (« {det[k].get('valeur')} »)" for k in corr.get("elements_non_trouves", [])) if corr.get("elements_non_trouves") else "") + ".")
    gen = (home.get("generateur") or {}).get("detectes") or []
    L.append("- Technologie détectée : " + (", ".join(x["nom"] for x in gen) or "non identifiée") + ".")
    L.append("- Risques : perte de pages non inventoriées, de l'historique Google si les redirections manquent, de formulaires ou d'espaces clients non visibles dans cet audit ; coordonnées à vérifier avec la fiche Google avant reprise.")
    L.append("")
    L.append("## Verdict motivé")
    L.append("")
    L.append(f"**{an['verdict']}** : {an['verdict_motif']}. Règle : « refonte pertinente » si ≥ 2 constats hauts ou 1 haut + 2 moyens ; « amélioration ciblée préférable » si ≥ 2 moyens sans haut ; « informations insuffisantes » si la page n'a pas pu être chargée ou moins de 3 constats fiables ; sinon « aucune amélioration substantielle établie ».")
    if an["non_verifie"]:
        L.append("")
        L.append("Limites : " + " ; ".join(an["non_verifie"]) + ". Les détections de ville, d'adresse et de services sont heuristiques et doivent être relues.")
    L.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# ----------------------------------------------------------------------------
# Programme principal
# ----------------------------------------------------------------------------

def strip_private(pages: list[dict]) -> list[dict]:
    out = []
    for p in pages:
        q = {k: v for k, v in p.items() if not k.startswith("_")}
        out.append(q)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit automatique, en lecture seule, du site d'un prospect.")
    ap.add_argument("url", help="URL du site (ex. https://exemple.fr/)")
    ap.add_argument("--out", required=True, help="dossier de sortie")
    ap.add_argument("--pages", type=int, default=4, help="nombre max de pages internes (défaut 4, max 4)")
    ap.add_argument("--ville", default=None, help="ville attendue (aide à la détection de zone)")
    ap.add_argument("--cp", default=None, help="code postal attendu")
    ap.add_argument("--nom", default=None, help="dénomination du lead (registre SIRENE) : recherchée sur le site pour « correspondance_entreprise »")
    ap.add_argument("--enseigne", default=None, help="enseigne du lead : même usage")
    ap.add_argument("--siren", default=None, help="SIREN du lead (9 chiffres) : recherché sur le site (SIRET compris)")
    ap.add_argument("--metier", default=None, help="libellé du métier (ex. « plombier chauffagiste ») : sert aux exemples des corrections")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="délai HTTP en secondes")
    ap.add_argument("--no-browser", action="store_true", help="ne pas lancer Playwright")
    ap.add_argument("--no-lighthouse", action="store_true", help="ne pas lancer Lighthouse")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2
    url = args.url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    if not urlparse(url).netloc:
        log("URL invalide")
        return 2
    pages_max = max(0, min(4, args.pages))
    os.makedirs(args.out, exist_ok=True)
    t_start = time.time()
    col = Collector(timeout=args.timeout)
    audit = {
        "meta": {"outil": "audit_site.py", "version": "1.1", "date": now_iso(), "user_agent": USER_AGENT,
                 "parametres": {"url": url, "pages": pages_max, "ville": args.ville, "cp": args.cp, "nom": args.nom,
                                "enseigne": args.enseigne, "siren": args.siren, "metier": args.metier,
                                "timeout_s": args.timeout, "navigateur": not args.no_browser, "lighthouse": not args.no_lighthouse}},
        "cible": {"url_demandee": url, "domaine_demande": host_base(urlparse(url).netloc), "url_finale": None,
                  "domaine_final": None, "hote_final": None, "status": None, "chaine": [], "erreur": None},
        "http": {"hsts": None, "test_http": None, "test_https": None, "test_www": None, "serveur": None},
        "pages": [], "robots": {}, "sitemap": {}, "navigateur": None, "lighthouse": None, "analyse": None,
        "erreurs": [], "journal_requetes": [],
    }
    try:
        # 1. Accueil
        log(f"GET {url}")
        home_res = col.get(url, kind="html")
        audit["cible"].update({"url_finale": home_res.get("final_url"), "status": home_res.get("status"),
                               "chaine": home_res.get("chaine"), "erreur": home_res.get("erreur")})
        home_url = home_res.get("final_url") or url
        if home_res.get("final_url"):
            fnet = urlparse(home_res["final_url"]).netloc
            audit["cible"]["hote_final"] = fnet.lower()
            audit["cible"]["domaine_final"] = host_base(fnet)
        h = home_res.get("headers") or {}
        audit["http"]["hsts"] = h.get("strict-transport-security")
        audit["http"]["serveur"] = h.get("server")
        home_page = analyse_page(url, home_res, "accueil")
        audit["pages"].append(home_page)

        # 2. Redirections http → https et www
        fp = urlparse(home_url)
        if home_res.get("status"):
            if fp.scheme == "https":
                http_url = urlunparse(("http", fp.netloc, "/", "", "", ""))
                log(f"test http : {http_url}")
                t = col.get(http_url, kind="html", read_body=False)
                audit["http"]["test_http"] = {k: t.get(k) for k in ("url", "status", "final_url", "chaine", "erreur", "duree_s")}
            else:
                https_url = urlunparse(("https", fp.netloc, "/", "", "", ""))
                log(f"test https : {https_url}")
                t = col.get(https_url, kind="html", read_body=False)
                audit["http"]["test_https"] = {k: t.get(k) for k in ("url", "status", "final_url", "chaine", "erreur", "duree_s")}
            host = fp.netloc
            alt_host = host[4:] if host.lower().startswith("www.") else "www." + host
            www_url = urlunparse((fp.scheme, alt_host, "/", "", "", ""))
            log(f"test www : {www_url}")
            w = col.get(www_url, kind="html", read_body=False)
            audit["http"]["test_www"] = {k: w.get(k) for k in ("url", "status", "final_url", "chaine", "erreur", "duree_s")}

        # 3. Pages internes
        chosen = choose_internal_pages(home_page, pages_max)
        for ch in chosen:
            log(f"page interne ({ch['categorie']}) : {ch['url']}")
            r = col.get(ch["url"], kind="html")
            audit["pages"].append(analyse_page(ch["url"], r, ch["categorie"]))

        # 4. robots / sitemap
        origin = f"{fp.scheme}://{fp.netloc}"
        if home_res.get("status"):
            audit["robots"] = check_robots(col, origin)
            audit["sitemap"] = check_sitemap(col, origin, audit["robots"])
        else:
            audit["robots"] = {"existe": False, "erreur": "accueil injoignable, non testé"}
            audit["sitemap"] = {"existe": False, "erreur": "accueil injoignable, non testé", "testees": []}

        # 5. Navigateur
        if not args.no_browser and home_res.get("status"):
            log("navigateur Playwright (375×812 puis 1440×900)")
            audit["navigateur"] = run_browser(home_url, args.out)
        elif args.no_browser:
            audit["navigateur"] = {"erreur": "désactivé (--no-browser)", "vues": {}}
        else:
            audit["navigateur"] = {"erreur": "accueil injoignable, non lancé", "vues": {}}

        # 6. Lighthouse
        lh_path = os.path.join(args.out, "lighthouse.json")
        if not args.no_lighthouse and home_res.get("status"):
            log("Lighthouse mobile (≈20 s)")
            audit["lighthouse"] = run_lighthouse(home_url, lh_path)
        else:
            audit["lighthouse"] = {"statut": "non mesuré", "raison": "désactivé (--no-lighthouse)" if args.no_lighthouse else "accueil injoignable"}
    except Exception as e:  # noqa: BLE001
        audit["erreurs"].append(f"collecte : {type(e).__name__} : {e}")
        log(traceback.format_exc())

    # 7. Analyse
    try:
        audit["analyse"] = analyse(audit, {"ville": args.ville, "cp": args.cp, "nom": args.nom, "enseigne": args.enseigne,
                                           "siren": args.siren, "metier": args.metier})
    except Exception as e:  # noqa: BLE001
        audit["erreurs"].append(f"analyse : {type(e).__name__} : {e}")
        log(traceback.format_exc())
        audit["analyse"] = {"constats": [], "non_verifie": [f"analyse interrompue : {e}"], "verdict": "informations insuffisantes",
                            "verdict_motif": "erreur interne pendant l'analyse", "gravites": {"haute": 0, "moyenne": 0, "basse": 0},
                            "ce_qui_fonctionne": [], "a_preserver": {"pages_trouvees": [], "menu": [], "coordonnees": {"telephones": [], "emails": [], "adresses": []}, "services_listes": [], "note": ""},
                            "correspondance_entreprise": {"elements_trouves": [], "elements_fournis": [], "elements_non_trouves": [], "details": {}, "note": "analyse interrompue"}}

    audit["pages"] = strip_private(audit["pages"])
    audit["journal_requetes"] = col.journal
    audit["meta"]["requetes_html"] = col.html_requests
    audit["meta"]["requetes_autres"] = col.other_requests
    audit["meta"]["duree_totale_s"] = round(time.time() - t_start, 1)

    # 8. Sorties
    json_path = os.path.join(args.out, "audit.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2, default=str)
    md_path = os.path.join(args.out, "audit.md")
    try:
        write_markdown(audit, md_path)
    except Exception as e:  # noqa: BLE001
        audit["erreurs"].append(f"markdown : {type(e).__name__} : {e}")
        log(traceback.format_exc())
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Audit de {url}\n\nRapport Markdown non généré ({e}). Voir audit.json.\n")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(audit, f, ensure_ascii=False, indent=2, default=str)

    an = audit["analyse"]
    corr = an.get("correspondance_entreprise") or {}
    summary = {"url": url, "url_finale": audit["cible"].get("url_finale"),
               "domaine_demande": audit["cible"].get("domaine_demande"), "domaine_final": audit["cible"].get("domaine_final"),
               "verdict": an["verdict"], "constats": len(an["constats"]), "gravites": an["gravites"],
               "lighthouse_performance": ((audit.get("lighthouse") or {}).get("scores") or {}).get("performance"),
               "correspondance_entreprise": corr.get("elements_trouves", []),
               "correspondance_non_trouves": corr.get("elements_non_trouves", []),
               "duree_s": audit["meta"]["duree_totale_s"], "out": os.path.abspath(args.out),
               "erreurs": audit["erreurs"]}
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
