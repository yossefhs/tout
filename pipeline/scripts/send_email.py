#!/usr/bin/env python3
"""Envoi d'un e-mail de prospection produit par build_email.py.

Fournisseurs :
  brevo        : API HTTP Brevo v3 (https://api.brevo.com/v3/smtp/email). Clé lue dans BREVO_API_KEY
                 ou injectée par le proxy de l'environnement (secret réseau pour api.brevo.com, en-tête api-key).
  gmail-draft  : n'envoie rien ; écrit le JSON prêt pour l'outil Gmail create_draft (la session fait l'appel).
  smtp         : envoi SMTP authentifié (ex. OVH : ssl0.ovh.net:465 SSL) depuis email_envoi. Identifiants lus dans
                 SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD ou dans le fichier JSON désigné par SMTP_CREDENTIALS_FILE
                 ({"host","port","user","password"}) ; jamais affichés. Prévu pour une exécution sur le Mac (Remote Control).
Garde-fous : refus si l'adresse ou le domaine est en opposition, si le domaine est déjà dans le registre avec un statut
sent/replied/stop/bounced/interested, si le plafond quotidien (config.plafond_quotidien) est atteint, ou hors des
heures d'envoi (config.heures_envoi, jours ouvrés, Europe/Paris). --dry-run simule tout sans appel réseau.
Chaque envoi réel est consigné dans data/ledger.csv (statut sent, notes = fournisseur + messageId).
"""
import argparse, csv, datetime as dt, json, os, subprocess, sys
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
P = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(P, "data", "ledger.csv")
OPPO = os.path.join(P, "data", "opposition.csv")

def read_csv(path):
    if not os.path.exists(path): return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))

def domain_of(email):
    return email.split("@", 1)[1].lower().strip() if "@" in email else ""

def load_config():
    with open(os.path.join(P, "config.json"), encoding="utf-8") as f:
        return json.load(f)

def within_hours(cfg, now):
    h = cfg.get("heures_envoi", {"debut": "09:00", "fin": "18:00", "jours": [0, 1, 2, 3, 4]})
    if now.weekday() not in h.get("jours", [0, 1, 2, 3, 4]): return False
    t = now.strftime("%H:%M")
    return h.get("debut", "09:00") <= t <= h.get("fin", "18:00")

def sent_today(now):
    today = now.strftime("%Y-%m-%d")
    return sum(1 for r in read_csv(LEDGER) if r.get("statut") == "sent" and (r.get("date") or "").startswith(today))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email-json", required=True, help="email.json produit par build_email.py")
    ap.add_argument("--to", required=True, help="adresse du destinataire")
    ap.add_argument("--to-name", default="")
    ap.add_argument("--siren", default="")
    ap.add_argument("--subject-index", type=int, default=0, help="0 ou 1 : lequel des deux objets utiliser")
    ap.add_argument("--provider", choices=["brevo", "gmail-draft", "smtp"], default=None, help="défaut : config.envoi.fournisseur")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-hours", action="store_true", help="ignorer la fenêtre horaire (tests)")
    ap.add_argument("--out", default=None, help="chemin du JSON résultat (gmail-draft ou trace d'envoi)")
    a = ap.parse_args()

    cfg = load_config()
    envoi = cfg.get("envoi", {})
    provider = a.provider or envoi.get("fournisseur", "gmail-draft")
    exp = cfg.get("expediteur", {})
    sender_email = envoi.get("email_envoi") or exp.get("email_envoi") or exp.get("email_reponse")
    sender_name = exp.get("nom", "Clients Ici")
    reply_to = exp.get("email_reponse", sender_email)
    tz = ZoneInfo("Europe/Paris") if ZoneInfo else None
    now = dt.datetime.now(tz) if tz else dt.datetime.now()

    with open(a.email_json, encoding="utf-8") as f:
        em = json.load(f)
    subjects = em.get("objets") or em.get("subjects") or []
    body = em.get("corps") or em.get("body") or ""
    if not subjects or not body:
        print("email.json incomplet (objets/corps manquants)", file=sys.stderr); return 2
    subject = subjects[min(a.subject_index, len(subjects) - 1)]
    to = a.to.strip().lower(); dom = domain_of(to)

    # Garde-fous
    oppo = {r.get("valeur", "").lower() for r in read_csv(OPPO)}
    WEBMAILS = {"gmail.com","orange.fr","wanadoo.fr","free.fr","sfr.fr","laposte.net","hotmail.fr","hotmail.com","outlook.fr","outlook.com","yahoo.fr","yahoo.com","live.fr","icloud.com","neuf.fr","bbox.fr","numericable.fr","aol.com","gmx.fr","protonmail.com","proton.me"}
    if to in oppo or (dom in oppo and dom not in WEBMAILS):
        print(f"REFUS : {to} ou {dom} est en liste d'opposition", file=sys.stderr); return 3
    for r in read_csv(LEDGER):
        if (r.get("domaine", "").lower() == dom or r.get("email", "").lower() == to) and r.get("statut") in ("sent", "replied", "stop", "bounced", "interested", "won", "lost"):
            print(f"REFUS : {dom} déjà contacté (statut {r.get('statut')} le {r.get('date')})", file=sys.stderr); return 3
    cap = int(cfg.get("plafond_quotidien", 10))
    if sent_today(now) >= cap:
        print(f"REFUS : plafond quotidien atteint ({cap})", file=sys.stderr); return 4
    if not a.force_hours and not within_hours(cfg, now):
        print("REFUS : hors des heures d'envoi configurées", file=sys.stderr); return 4

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to, **({"name": a.to_name} if a.to_name else {})}],
        "replyTo": {"email": reply_to, "name": sender_name},
        "subject": subject,
        "textContent": body,
        "headers": {"List-Unsubscribe": f"<mailto:{reply_to}?subject=STOP>"},
        "tags": ["prospection-refonte"],
    }
    if provider == "gmail-draft" or a.dry_run:
        draft = {"to": [to], "subject": subject, "body": body, "note": "Utiliser l'outil Gmail create_draft (mode review) ou send_message (mode auto) avec ces champs ; l'expéditeur sera le compte Gmail connecté."}
        out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.email_json)), "gmail_draft.json" if provider == "gmail-draft" else "send_dry_run.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(draft if provider == "gmail-draft" else payload, f, ensure_ascii=False, indent=1)
        print(("DRY-RUN " if a.dry_run else "") + f"{provider} : rien n'a été envoyé ; JSON écrit dans {out}")
        return 0

    if provider == "smtp":
        import smtplib, ssl
        from email.message import EmailMessage
        from email.utils import formataddr, make_msgid
        creds = {"host": os.environ.get("SMTP_HOST", ""), "port": os.environ.get("SMTP_PORT", "465"),
                 "user": os.environ.get("SMTP_USER", ""), "password": os.environ.get("SMTP_PASSWORD", "")}
        cf = os.environ.get("SMTP_CREDENTIALS_FILE")
        if cf and os.path.exists(cf):
            with open(cf, encoding="utf-8") as f:
                creds.update({k: str(v) for k, v in json.load(f).items() if k in creds})
        if not (creds["host"] and creds["user"] and creds["password"]):
            print("ÉCHEC smtp : identifiants absents (SMTP_HOST/SMTP_USER/SMTP_PASSWORD ou SMTP_CREDENTIALS_FILE)", file=sys.stderr); return 5
        msg = EmailMessage()
        msg["From"] = formataddr((sender_name, sender_email)); msg["To"] = to
        msg["Reply-To"] = formataddr((sender_name, reply_to)); msg["Subject"] = subject
        msg["List-Unsubscribe"] = payload["headers"]["List-Unsubscribe"]; msg["Message-ID"] = make_msgid(domain=domain_of(sender_email) or None)
        msg.set_content(body)
        try:
            port = int(creds["port"] or 465)
            if port == 465:
                srv = smtplib.SMTP_SSL(creds["host"], port, timeout=30, context=ssl.create_default_context())
            else:
                srv = smtplib.SMTP(creds["host"], port, timeout=30); srv.starttls(context=ssl.create_default_context())
            with srv:
                srv.login(creds["user"], creds["password"]); srv.send_message(msg)
        except Exception as e:
            print(f"ÉCHEC smtp : {type(e).__name__}", file=sys.stderr); return 5
        mid = msg["Message-ID"]
        subprocess.run([sys.executable, os.path.join(P, "scripts", "ledger.py"), "add", "--siren", a.siren, "--domaine", dom, "--email", to, "--statut", "sent", "--notes", f"smtp {mid}"], check=False)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f: json.dump({"provider": "smtp", "messageId": mid, "to": to, "subject": subject}, f, ensure_ascii=False, indent=1)
        print(f"ENVOYÉ via SMTP à {to} (Message-ID {mid})")
        return 0

    # Envoi réel Brevo
    import urllib.request, urllib.error
    key = os.environ.get("BREVO_API_KEY", "")
    req = urllib.request.Request("https://api.brevo.com/v3/smtp/email", data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "Accept": "application/json", **({"api-key": key} if key else {"api-key": "injected-by-proxy"})})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        print(f"ÉCHEC Brevo HTTP {e.code} : {e.read().decode('utf-8', 'replace')[:300]}", file=sys.stderr); return 5
    except Exception as e:
        print(f"ÉCHEC Brevo : {e}", file=sys.stderr); return 5
    mid = res.get("messageId", "")
    subprocess.run([sys.executable, os.path.join(P, "scripts", "ledger.py"), "add", "--siren", a.siren, "--domaine", dom, "--email", to, "--statut", "sent", "--notes", f"brevo {mid}"], check=False)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f: json.dump({"provider": "brevo", "messageId": mid, "to": to, "subject": subject}, f, ensure_ascii=False, indent=1)
    print(f"ENVOYÉ via Brevo à {to} (messageId {mid})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
