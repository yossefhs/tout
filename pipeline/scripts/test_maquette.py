#!/home/user/.venv-webtest/bin/python
"""test_maquette.py — vérifie une ou plusieurs maquettes (build_maquette.py) avec Playwright.

Usage :
  test_maquette.py <dossier> [--out <dossier_captures>] [--port N] [--lighthouse]
  <dossier> contient soit index.html, soit des sous-dossiers contenant chacun un index.html.

Contrôles : 375/768/1440 px (débordement horizontal, éléments hors cadre, erreurs console/JS, captures),
formulaire (validation locale, message « Démonstration : ce formulaire n'envoie rien. », aucune requête
réseau émise), aucune requête hors du serveur local à aucune largeur (toute requête externe est bloquée avant d'être
émise et comptée KO), parcours clavier (lien d'évitement en premier, focus visible), garde-fous (aucun lien
tel:/mailto:, meta noindex, bandeau, mention de pied de page, un seul H1, texte ≥ 12 px).
--lighthouse : lance Lighthouse 12 (mobile) sur chaque maquette ; SEO ≈ 60 attendu (noindex voulu).
Sortie : JSON sur stdout ; code 0 si 0 KO, 1 sinon (requête externe, bandeau de démonstration absent, débordement…).
"""
import argparse, functools, http.server, json, os, shutil, subprocess, sys, threading

ICI = os.path.dirname(os.path.abspath(__file__))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/home/user/.venv-webtest/ms-playwright"  # navigateurs du venv (1.64.1)
os.environ.setdefault("CHROME_PATH", "/opt/pw-browsers/chromium-1243/chrome-linux64/chrome")
MSG_DEMO = "Démonstration : ce formulaire n'envoie rien."


def serveur(dossier, port):
    class Silencieux(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass
    h = functools.partial(Silencieux, directory=dossier)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def tester(base, rel, outdir, nom):
    """Teste une maquette ; toute anomalie va dans r["ko"] (le code de retour du script vaut 1 dès qu'un KO existe)."""
    from playwright.sync_api import sync_playwright
    r = {"ko": [], "captures": []}
    url = f"{base}/{rel}".replace("//index", "/index")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        for w, h in ((375, 812), (768, 1024), (1440, 900)):
            ctx = b.new_context(viewport={"width": w, "height": h}, locale="fr-FR")
            pg = ctx.new_page()
            reqs, errs, pgerrs, externes = [], [], [], []

            def router(route, rq, _ext=externes):
                # seule la maquette servie en local est autorisée : tout le reste est bloqué et compté KO
                if rq.url.startswith(base + "/"):
                    route.continue_()
                else:
                    _ext.append(rq.url); route.abort()
            ctx.route("**/*", router)
            pg.on("request", lambda rq: reqs.append(rq.url))
            pg.on("console", lambda m: errs.append(m.text) if m.type in ("error", "warning") else None)
            pg.on("pageerror", lambda e: pgerrs.append(str(e)))
            pg.goto(url); pg.wait_for_load_state("networkidle")
            sw, iw = pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            if sw > iw: r["ko"].append(f"{w}px : débordement horizontal {sw} > {iw}")
            over = pg.evaluate("() => [...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>window.innerWidth+1).slice(0,5).map(e=>e.tagName+'.'+e.className)")
            if over: r["ko"].append(f"{w}px : éléments hors cadre {over}")
            if outdir:
                cap = os.path.join(outdir, f"{nom}-{w}.png"); pg.screenshot(path=cap, full_page=True); r["captures"].append(cap)
            if externes: r["ko"].append(f"{w}px : requête(s) externe(s) bloquée(s) {externes[:5]}")
            if errs: r["ko"].append(f"{w}px : console {errs}")
            if pgerrs: r["ko"].append(f"{w}px : erreurs JS {pgerrs}")
            if w == 375:
                n0 = len(reqs)
                pg.click("#formulaire button[type=submit]")
                st = pg.inner_text("#statut"); inval = pg.locator("#formulaire label.invalide").count()
                if inval == 0 or "compléter" not in st: r["ko"].append(f"validation à vide : statut='{st}', invalides={inval}")
                pg.fill("#formulaire [name=nom]", "Jean Test")
                if pg.locator("#formulaire [name=tel]").count(): pg.fill("#formulaire [name=tel]", "0600000000")
                if pg.locator("#formulaire [name=email]").count(): pg.fill("#formulaire [name=email]", "jean@test.example")
                pg.fill("#formulaire [name=message]", "Bonjour, test.")
                pg.click("#formulaire button[type=submit]"); pg.wait_for_timeout(400)
                st = pg.inner_text("#statut")
                if st != MSG_DEMO: r["ko"].append(f"statut après envoi : '{st}'")
                if pg.locator("#formulaire label.invalide").count(): r["ko"].append("champs encore invalides après saisie valide")
                if len(reqs) != n0: r["ko"].append(f"requêtes émises par le formulaire : {reqs[n0:]}")
                if pg.url != url: r["ko"].append(f"navigation après envoi : {pg.url}")
                r["requetes_reseau"] = list(reqs)
                r["requetes_externes"] = list(externes)
                if len(reqs) != 1: r["ko"].append(f"requêtes réseau inattendues : {reqs}")
                pg.goto(url); pg.wait_for_load_state("networkidle")
                ordre, sans = [], []
                for _ in range(60):
                    pg.keyboard.press("Tab")
                    info = pg.evaluate("""() => {const e=document.activeElement; if(!e||e===document.body) return null;
                      const cs=getComputedStyle(e); return {tag:e.tagName, txt:(e.textContent||e.name||'').trim().slice(0,30), outline:cs.outlineStyle, ow:cs.outlineWidth, fv:e.matches(':focus-visible')}}""")
                    if not info: break
                    ordre.append(f"{info['tag']}:{info['txt']}")
                    if info["fv"] and (info["outline"] == "none" or info["ow"] == "0px"): sans.append(info)
                r["parcours_clavier"] = ordre
                if sans: r["ko"].append(f"focus non visible : {sans}")
                if not ordre or not ordre[0].startswith("A:Aller au contenu"): r["ko"].append(f"lien d'évitement absent en premier : {ordre[:2]}")
                if pg.locator("a[href^='tel:'], a[href^='mailto:']").count(): r["ko"].append("liens tel:/mailto: présents")
                if pg.get_attribute("meta[name=robots]", "content") != "noindex, nofollow": r["ko"].append("meta noindex absente")
                if not pg.locator(".avis:has-text('Proposition non officielle')").count(): r["ko"].append("bandeau de démonstration absent")
                if not pg.locator("footer:has-text('aucune donnée collectée')").count(): r["ko"].append("mention de pied de page absente")
                r["h1"] = pg.locator("h1").count()
                if r["h1"] != 1: r["ko"].append(f"nombre de H1 : {r['h1']}")
                mn = pg.evaluate("""() => {let m=99;for(const e of document.querySelectorAll('body *')){if(e.children.length||!e.textContent.trim())continue;const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden')continue;m=Math.min(m,parseFloat(cs.fontSize))}return m}""")
                r["texte_min_px"] = mn
                if mn < 12: r["ko"].append(f"texte de {mn}px (< 12 px)")
            ctx.close()
        b.close()
    return r


def lighthouse(url, out_json):
    npx = shutil.which("npx")
    if not npx: return {"erreur": "npx introuvable"}
    cmd = [npx, "-y", "lighthouse@12", url, "--chrome-flags=--headless=new --no-sandbox --disable-gpu", "--form-factor=mobile",
           "--screenEmulation.mobile", "--throttling-method=simulate",
           "--only-categories=performance,accessibility,best-practices,seo", "--output=json", f"--output-path={out_json}", "--quiet"]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        d = json.load(open(out_json, encoding="utf-8"))
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as e:
        return {"erreur": f"lighthouse : {e}"}
    scores = {k: round((v.get("score") or 0) * 100) for k, v in d.get("categories", {}).items()}
    echecs = [k for k, a in d.get("audits", {}).items() if a.get("score") is not None and a["score"] < 0.9 and a.get("scoreDisplayMode") in ("binary", "numeric")]
    return {"scores": scores, "audits_en_echec": echecs}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dossier"); ap.add_argument("--out"); ap.add_argument("--port", type=int, default=0, help="0 = port libre choisi par le système"); ap.add_argument("--lighthouse", action="store_true")
    a = ap.parse_args()
    dossier = os.path.abspath(a.dossier)
    if os.path.isfile(os.path.join(dossier, "index.html")):
        cibles = {os.path.basename(dossier.rstrip("/")): "index.html"}
    else:
        cibles = {d: f"{d}/index.html" for d in sorted(os.listdir(dossier)) if os.path.isfile(os.path.join(dossier, d, "index.html"))}
    if not cibles:
        print(json.dumps({"erreur": "aucun index.html trouvé"})); return 2
    if a.out: os.makedirs(a.out, exist_ok=True)
    srv = serveur(dossier, a.port); base = f"http://127.0.0.1:{srv.server_address[1]}"
    res = {}
    try:
        for nom, rel in cibles.items():
            try:
                res[nom] = tester(base, rel, a.out, nom)
            except Exception as e:  # navigateur en échec : compté KO, on continue
                res[nom] = {"ko": [f"exception : {e}"]}
            if a.lighthouse:
                lj = os.path.join(a.out or dossier, f"lighthouse-{nom}.json")
                res[nom]["lighthouse"] = lighthouse(f"{base}/{rel}", lj)
                lh = res[nom]["lighthouse"]
                if "erreur" in lh: res[nom]["ko"].append(lh["erreur"])
                else:
                    for k in ("performance", "accessibility", "best-practices"):
                        if lh["scores"].get(k, 0) < 90: res[nom]["ko"].append(f"lighthouse {k} = {lh['scores'].get(k)}")
                    if [x for x in lh["audits_en_echec"] if x != "is-crawlable"]: res[nom]["ko"].append(f"lighthouse audits : {lh['audits_en_echec']}")
    finally:
        srv.shutdown()
    total = sum(len(v["ko"]) for v in res.values())
    print(json.dumps({"ko_total": total, "maquettes": res}, ensure_ascii=False, indent=1))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
