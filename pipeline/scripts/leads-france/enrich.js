#!/usr/bin/env node
/**
 * ENRICH v2 — Enrichit un CSV de leads avec site web + contacts publics VÉRIFIÉS
 *
 * Cascade de détection du site (du plus fiable au moins fiable) :
 *  1. Devinette de domaine directe : nom-entreprise.fr / .com (gratuit, instantané)
 *  2. Recherche DuckDuckGo en DERNIER recours (fragile, throttlée)
 * Chaque site candidat est VÉRIFIÉ : le SIREN, le nom ou la ville doivent
 * apparaître sur la page → colonne site_confiance (haute/moyenne/basse).
 *
 * Contacts :
 *  - JSON-LD schema.org d'abord (données structurées), puis regex
 *  - emails validés par lookup DNS MX (élimine les domaines morts)
 *
 * ⚠️ RGPD : ne collecte que des coordonnées PROFESSIONNELLES rendues
 * publiques par l'entreprise elle-même (intérêt légitime B2B, art. 6.1.f).
 * Toujours offrir un opt-out dans tes campagnes.
 *
 * Usage :
 *   node enrich.js leads.csv --out leads-enrichis.csv --max 50 --concurrence 4
 */

const fs = require('fs');
const dns = require('dns').promises;

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
// Pipeline Clients Ici : User-Agent identifiable (lecture seule, politique de courtoisie)
const UA = process.env.ENRICH_UA || 'Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/)';

function parseArgs(argv) {
  const a = { _: [] };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith('--')) {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) a[k.slice(2)] = true;
      else { a[k.slice(2)] = next; i++; }
    } else a._.push(k);
  }
  return a;
}

// ---------- CSV ----------
function parseCSV(text) {
  const lines = text.replace(/^\ufeff/, '').split('\n').filter(l => l.trim());
  const sep = lines[0].includes(';') ? ';' : ',';
  const parseLine = (line) => {
    const out = []; let cur = '', inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (inQ) {
        if (c === '"' && line[i + 1] === '"') { cur += '"'; i++; }
        else if (c === '"') inQ = false;
        else cur += c;
      } else {
        if (c === '"') inQ = true;
        else if (c === sep) { out.push(cur); cur = ''; }
        else cur += c;
      }
    }
    out.push(cur);
    return out;
  };
  const cols = parseLine(lines[0]);
  return { cols, rows: lines.slice(1).map(l => {
    const vals = parseLine(l);
    return Object.fromEntries(cols.map((c, i) => [c, vals[i] ?? '']));
  }) };
}

function toCSV(rows) {
  if (!rows.length) return '';
  const cols = [...new Set(rows.flatMap(r => Object.keys(r)))];
  const esc = (v) => { const s = String(v ?? ''); return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return [cols.join(';'), ...rows.map(r => cols.map(c => esc(r[c])).join(';'))].join('\n');
}

// ---------- HTTP ----------
async function fetchText(url, timeout = 10000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(url, { headers: { 'User-Agent': UA }, signal: ctrl.signal, redirect: 'follow' });
    const ct = res.headers.get('content-type') || '';
    if (!res.ok || (!ct.includes('text') && !ct.includes('html'))) {
      try { await res.body?.cancel(); } catch { /* corps déjà fermé */ } // libère la connexion (sinon le processus peut ne jamais se terminer)
      return null;
    }
    // plafond de taille : 2 Mo de HTML suffisent largement pour vérifier un site et y lire un contact
    const buf = await res.arrayBuffer();
    return new TextDecoder('utf-8').decode(buf.byteLength > 2_000_000 ? buf.slice(0, 2_000_000) : buf);
  } catch { return null; }
  finally { clearTimeout(t); }
}

// ---------- Normalisation du nom ----------
const FORMES = /\b(sarl|sas|sasu|eurl|sci|snc|scp|sel|selarl|selas|sccv|scm|gie|ei|earl|gaec|monsieur|madame|m|mme|ste|societe|société|ets|etablissements?)\b/gi;
const strip = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

function nameTokens(lead) {
  // le nom "officiel" + l'enseigne commerciale, sans formes juridiques ni sigle entre parenthèses
  const raw = `${lead.nom || lead.denomination || ''} ${lead.enseigne || ''}`.replace(/\([^)]*\)/g, ' ');
  return [...new Set(strip(raw).replace(FORMES, ' ').replace(/[^a-z0-9]+/g, ' ').trim().split(/\s+/).filter(w => w.length >= 2))];
}

// Pipeline Clients Ici : les TPE/EI s'appellent souvent « PRENOM NOM (ENSEIGNE) » ; le site porte
// l'enseigne seule (nico-elec.fr) ou le nom seul, rarement la concaténation des deux.
// On génère donc des bases distinctes : enseigne seule, nom seul, puis nom+enseigne (comportement d'origine).
function tokensOf(txt) {
  return [...new Set(strip(String(txt || '').replace(/\([^)]*\)/g, ' ')).replace(FORMES, ' ').replace(/[^a-z0-9]+/g, ' ').trim().split(/\s+/).filter(w => w.length >= 3))];
}
function basesFromTokens(tokens) {
  const t = tokens.slice(0, 4), out = [];
  if (!t.length) return out;
  if (t.length > 1) { out.push(t.join('')); out.push(t.join('-')); }
  else if (t[0].length >= 6 || (t[0].length >= 5 && /\d/.test(t[0]))) out.push(t[0]); // 1 seul mot : exiger un nom long ou un sigle chiffré (sinon trop de faux positifs)
  return out;
}
function domainCandidates(lead) {
  const nom = lead.nom || lead.denomination || '';
  const enseigne = lead.enseigne || '';
  const bases = new Set();
  // 1. enseigne(s) seule(s) — plusieurs enseignes possibles séparées par des virgules
  for (const e of String(enseigne).split(',')) basesFromTokens(tokensOf(e)).forEach(b => bases.add(b));
  // 2. nom seul (sans le contenu entre parenthèses, souvent l'enseigne ou le sigle)
  basesFromTokens(tokensOf(nom)).forEach(b => bases.add(b));
  // 3. sigle / contenu entre parenthèses seul (ex : « (EPV28) »)
  for (const m of String(nom).matchAll(/\(([^)]+)\)/g)) basesFromTokens(tokensOf(m[1])).forEach(b => bases.add(b));
  // 4. nom + enseigne combinés (comportement d'origine)
  basesFromTokens(nameTokens(lead)).forEach(b => bases.add(b));
  const out = [];
  for (const b of bases) if (b.length >= 5 && b.length <= 40) for (const tld of ['fr', 'com']) out.push(`https://${b}.${tld}`);
  return out.slice(0, 10);
}

// ---------- Vérification du site (anti-faux-positifs) ----------
// Pipeline Clients Ici : les mots de métier (« electricite », « plomberie », « services »…) sont présents sur
// n'importe quel annuaire ou plateforme du secteur : ils ne prouvent rien. Seuls les mots DISTINCTIFS du nom
// (patronyme, enseigne, sigle) comptent pour la vérification.
const GENERIQUES = new Set(`electricite electrique electricien elec plomberie plombier chauffage chauffagiste climatisation
clim sanitaire sanitaires thermique thermiques energie energies renouvelable renouvelables installation installations
installateur renovation renovations batiment batiments construction constructions travaux maison maisons habitat
menuiserie menuisier peinture peintre couverture couvreur charpente charpentier maconnerie macon isolation
depannage depannages artisan artisans entreprise entreprises services service generale general groupe france
solaire photovoltaique pompe chaleur eau gaz carrelage platrerie facade facades toiture toitures amenagement
agencement decoration design concept conseil conseils solutions solution technique techniques pro pros
coiffure coiffeur salon beaute esthetique institut boulangerie patisserie boulanger patissier restaurant brasserie
pizzeria bar cafe commerce magasin boutique atelier studio agence societe holding invest gestion patrimoine
immobilier immo centre nord sud est ouest centre-val loire eure loir chartres dreux
protection securite surete multiservices multi service24 depann`.split(/\s+/));
function distinctiveTokens(lead) {
  return nameTokens(lead).filter(w => w.length >= 4 && !GENERIQUES.has(w) && !/^\d+$/.test(w));
}
// Texte « lisible » d'une page : titre, metas, alt, corps sans scripts/styles/balises, normalisé (minuscules sans accents,
// séparateurs → espace). Les correspondances se font sur des MOTS entiers, jamais sur des sous-chaînes
// (« prest » ne doit pas matcher « prestation », « action » ne doit pas matcher l'attribut HTML action=).
function textOf(html) {
  let h = String(html || '');
  const title = (h.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [])[1] || '';
  const metas = [...h.matchAll(/<meta[^>]+content=["']([^"']{3,300})["']/gi)].map(m => m[1]).join(' ');
  const alts = [...h.matchAll(/\balt=["']([^"']{3,200})["']/gi)].map(m => m[1]).join(' ');
  h = h.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ').replace(/<[^>]+>/g, ' ');
  return ' ' + strip(`${title} ${metas} ${alts} ${h}`).replace(/&[a-z#0-9]+;/g, ' ').replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
}
const hasWord = (text, w) => !!w && text.includes(` ${w} `);
// phrase entière (« david elec », « hydro confort »), avec ou sans espaces (« davidelec » dans un logo/URL)
function hasPhrase(text, phrase) {
  if (!phrase) return false;
  if (text.includes(` ${phrase} `)) return true;
  const compact = phrase.replace(/ /g, '');
  return compact.length >= 8 && text.replace(/ /g, '').includes(compact);
}
function phrasesOf(lead) {
  const out = new Set();
  const clean = (t) => strip(String(t || '').replace(/\([^)]*\)/g, ' ')).replace(FORMES, ' ').replace(/[^a-z0-9]+/g, ' ').trim();
  for (const e of String(lead.enseigne || '').split(',')) { const c = clean(e); if (c) out.add(c); }
  const n = clean(lead.nom || lead.denomination || ''); if (n) out.add(n);
  for (const m of String(lead.nom || '').matchAll(/\(([^)]+)\)/g)) { const c = clean(m[1]); if (c) out.add(c); }
  // une phrase doit être discriminante : ≥ 2 mots, ou 1 mot distinctif de ≥ 6 caractères
  // 1 seul mot : ≥ 7 caractères ou un sigle chiffré (« cll28 »), pour écarter prénoms et mots courants (« daniel »)
  return [...out].filter(p => { const w = p.split(' '); return (w.length >= 2 && w.some(x => x.length >= 4 && !GENERIQUES.has(x))) || (w.length === 1 && !GENERIQUES.has(w[0]) && (w[0].length >= 7 || (w[0].length >= 5 && /\d/.test(w[0])))); });
}
function verifySite(htmls, lead) {
  const raw = htmls.join(' ');
  const digits = raw.replace(/[^0-9]/g, '');
  const siren = String(lead.siren || '').replace(/\D/g, '');
  if (siren.length === 9 && digits.includes(siren)) return 'haute'; // SIREN trouvé sur le site (mentions légales)
  const text = textOf(raw);
  const tokens = distinctiveTokens(lead);
  const hits = tokens.filter(t => hasWord(text, t)).length;
  const phrase = phrasesOf(lead).some(p => hasPhrase(text, p));
  // correspondance FORTE du nom : ≥ 2 mots distinctifs, ou la phrase complète, ou l'unique mot distinctif long
  const fort = hits >= 2 || phrase || (tokens.length === 1 && hits === 1 && tokens[0].length >= 7);
  if (!fort) return '';
  const ville = strip(lead.ville || lead.etab_zone_ville || '').replace(/[^a-z0-9]+/g, ' ').trim();
  const villeTok = ville.split(' ').filter(w => w.length >= 5 && !['saint', 'sainte', 'villages'].includes(w))[0] || '';
  const cp = String(lead.code_postal || lead.etab_zone_cp || '').replace(/\D/g, '');
  const ancre = (ville.length >= 4 && hasPhrase(text, ville)) || hasWord(text, villeTok) || (cp.length === 5 && digits.includes(cp));
  return ancre ? 'haute' : 'moyenne';
}

// ---------- Extraction de contacts ----------
function extractJSONLD(html) {
  const emails = new Set(), phones = new Set();
  for (const m of html.matchAll(/<script[^>]+application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)) {
    try {
      const walk = (o) => {
        if (!o || typeof o !== 'object') return;
        if (typeof o.email === 'string') emails.add(o.email.replace(/^mailto:/, '').toLowerCase());
        if (typeof o.telephone === 'string') phones.add(o.telephone);
        Object.values(o).forEach(walk);
      };
      walk(JSON.parse(m[1]));
    } catch { /* JSON-LD malformé : ignorer */ }
  }
  return { emails, phones };
}

function extractContacts(html) {
  const { emails, phones } = extractJSONLD(html);
  const clean = html.replace(/&#64;|&commat;/g, '@').replace(/\s*\[at\]\s*|\s*\(at\)\s*/gi, '@');
  for (const m of clean.matchAll(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g)) {
    const e = m[0].toLowerCase();
    if (!/\.(png|jpg|jpeg|gif|svg|webp|css|js)$/.test(e) && !/example|sentry|wixpress|@2x|\.local$/.test(e)) emails.add(e);
  }
  for (const m of clean.matchAll(/(?:\+33|0033|0)\s*[1-9](?:[\s.\-]?\d{2}){4}/g)) {
    const digits = m[0].replace(/\D/g, '');
    if (digits.length >= 10 && digits.length <= 12) phones.add(m[0].replace(/\s+/g, ' ').trim());
  }
  return { emails, phones };
}

// ---------- Validation MX (gratuite, native) ----------
const mxCache = new Map();
// Pipeline Clients Ici : certains environnements (bac à sable, proxy) ne servent pas les
// enregistrements MX en DNS natif (ENODATA). Secours : DNS-over-HTTPS (Google puis Cloudflare).
async function mxViaDoH(dom) {
  const endpoints = [
    { url: `https://dns.google/resolve?name=${encodeURIComponent(dom)}&type=MX`, headers: {} },
    { url: `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(dom)}&type=MX`, headers: { accept: 'application/dns-json' } },
  ];
  for (const ep of endpoints) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 5000);
    try {
      const res = await fetch(ep.url, { headers: { 'User-Agent': UA, ...ep.headers }, signal: ctrl.signal });
      if (!res.ok) continue;
      const j = await res.json();
      if (j && j.Status === 0) return (j.Answer || []).some(a => a.type === 15);
      if (j && j.Status === 3) return false; // NXDOMAIN : domaine inexistant
    } catch { /* endpoint suivant */ }
    finally { clearTimeout(t); }
  }
  return null; // indéterminé
}
async function mxOK(email) {
  const dom = email.split('@')[1];
  if (!dom) return false;
  if (mxCache.has(dom)) return mxCache.get(dom);
  let ok = false, nativeFailed = false;
  try { ok = ((await Promise.race([dns.resolveMx(dom), sleep(4000).then(() => [])])) || []).length > 0; }
  catch { nativeFailed = true; }
  if (!ok) {
    const doh = await mxViaDoH(dom);
    if (doh === true) ok = true;
    else if (doh === null && nativeFailed) ok = false; // ni natif ni DoH : on reste strict
  }
  mxCache.set(dom, ok);
  return ok;
}

// ---------- Recherche DDG (dernier recours, sérialisée) ----------
const BLOCKLIST = /societe\.com|pappers|annuaire-entreprises|verif\.com|infogreffe|linkedin|facebook|pagesjaunes|kompass|manageo|fr\.kompass|duckduckgo|wikipedia|lefigaro|bodacc|score3|b-reputation|entreprises\.lefigaro|mappy|yelp|tripadvisor|indeed|glassdoor|youtube|instagram|x\.com|twitter|doctolib|booking\.com|thefork|ubereats|deliveroo/i;
// Pipeline Clients Ici : liste éditable d'annuaires/agrégateurs (ENRICH_ANNUAIRES=chemin, un domaine par ligne).
// Une fiche d'annuaire cite le SIREN et la ville de l'entreprise : elle passerait la vérification
// alors qu'elle n'est PAS le site propre de l'entreprise.
const ANNUAIRES = new Set();
try {
  if (process.env.ENRICH_ANNUAIRES && fs.existsSync(process.env.ENRICH_ANNUAIRES)) {
    for (const l of fs.readFileSync(process.env.ENRICH_ANNUAIRES, 'utf8').split('\n')) {
      const d = l.trim().toLowerCase();
      if (d && !d.startsWith('#')) ANNUAIRES.add(d.replace(/^www\./, ''));
    }
  }
} catch { /* liste absente : on se contente de BLOCKLIST */ }
function estAnnuaire(url) {
  try {
    const h = new URL(url).hostname.toLowerCase().replace(/^www\./, '');
    for (const d of ANNUAIRES) if (h === d || h.endsWith('.' + d)) return true;
  } catch { return true; }
  return BLOCKLIST.test(url);
}
// Un résultat de recherche est ramené à la RACINE du site (https://hote/) : c'est la page d'accueil que l'on
// vérifie (nom + ville ou SIREN). La page profonde d'un annuaire ne peut plus passer pour un site propre.
function toOrigin(u) {
  try { const x = new URL(u); if (!/^https?:$/.test(x.protocol)) return null; return `${x.origin}/`; } catch { return null; }
}
let ddgLock = Promise.resolve();
let ddgChallenges = 0;
const METIERS = { '43.22A': 'plombier', '43.22B': 'chauffagiste', '43.21A': 'electricien', '43.21B': 'electricien', '43.29A': 'isolation',
  '43.31Z': 'platrier', '43.32A': 'menuisier', '43.32B': 'serrurier', '43.33Z': 'carreleur', '43.34Z': 'peintre', '43.39Z': 'renovation',
  '43.91A': 'charpentier', '43.91B': 'couvreur', '43.99C': 'macon', '43.99A': 'etancheite', '41.20A': 'constructeur', '81.30Z': 'paysagiste',
  '96.02A': 'coiffeur', '96.02B': 'esthetique', '96.04Z': 'bien-etre', '10.71C': 'boulangerie', '10.71D': 'patisserie', '47.24Z': 'boulangerie',
  '56.10A': 'restaurant', '56.10C': 'restaurant', '56.30Z': 'bar', '47.22Z': 'boucherie', '45.20A': 'garage', '75.00Z': 'veterinaire' };
async function ddgSearch(name, ville, metier) {
  const run = async () => {
    await sleep(1500); // throttle poli : DDG bloque vite
    const q = encodeURIComponent(`"${name}" ${metier || ''} ${ville || ''}`.replace(/\s+/g, ' ').trim());
    const html = await fetchText(`https://html.duckduckgo.com/html/?q=${q}`);
    if (!html) return [];
    if (/anomaly|challenge/i.test(html) && !/uddg=/.test(html)) { ddgChallenges++; return []; } // page anti-robot : pas de résultats
    const seen = new Set(), out = [];
    for (const m of html.matchAll(/uddg=([^&"]+)/g)) {
      const o = toOrigin(decodeURIComponent(m[1]));
      if (!o || seen.has(o) || estAnnuaire(o)) continue;
      seen.add(o); out.push(o);
      if (out.length >= 4) break;
    }
    return out;
  };
  const p = ddgLock.then(run, run);
  ddgLock = p.catch(() => {});
  return p;
}

// ---------- Enrichissement d'un lead ----------
const CONTACT_PATHS = ['/contact', '/contact/', '/nous-contacter', '/mentions-legales', '/mentions-legales/'];

async function tryCandidate(url, lead, minConf = 'moyenne') {
  const home = await fetchText(url, 8000);
  if (!home || home.length < 300) return null;
  const pages = [home];
  let conf = verifySite(pages, lead);
  // chercher le SIREN sur les mentions légales pour monter en confiance
  if (conf !== 'haute') {
    const ml = await fetchText(url.replace(/\/+$/, '') + '/mentions-legales', 6000);
    if (ml) { pages.push(ml); conf = verifySite(pages, lead); }
  }
  if (!conf) return null;
  if (minConf === 'haute' && conf !== 'haute') return null;
  return { url, pages, conf };
}

async function enrichOne(lead, useDDG) {
  const name = lead.nom || lead.denomination || '';
  if (!name) return { ...lead, site_web: '', site_confiance: '', emails_publics: '', telephones_publics: '' };

  let found = null;
  // 1. devinette de domaine directe (fiable et instantanée)
  // Nom à 1 seul mot distinctif : le domaine contient forcément le nom (preuve circulaire)
  // → on exige SIREN ou ville sur le site pour éviter les homonymes.
  // Entrepreneur individuel sans enseigne (nom = une personne) : homonymes fréquents → on exige aussi 'haute'.
  lead.__personne = String(lead.forme_juridique || '') === '1000' && !String(lead.enseigne || '').trim();
  const minConf = distinctiveTokens(lead).length >= 2 && !lead.__personne ? 'moyenne' : 'haute';
  for (const url of domainCandidates(lead)) {
    found = await tryCandidate(url, lead, minConf);
    if (found) break;
  }
  // 2. DuckDuckGo en dernier recours (même exigence de confiance)
  if (!found && useDDG) {
    const enseigne = String(lead.enseigne || '').split(',')[0].trim();
    const requete = enseigne || name.replace(/\([^)]*\)/g, ' ').replace(/\s+/g, ' ').trim();
    const urls = await ddgSearch(requete, lead.ville || lead.etab_zone_ville, METIERS[String(lead.naf || '').trim()]);
    for (const url of urls) {
      const r = await tryCandidate(url, lead, minConf);
      if (r) { found = r; break; }
    }
    // rien de vérifié : prendre le 1er résultat plausible, marqué basse confiance
    if (!found && urls[0]) {
      const home = await fetchText(urls[0], 8000);
      if (home) found = { url: urls[0], pages: [home], conf: 'basse' };
    }
  }

  let emails = new Set(), phones = new Set();
  if (found) {
    for (const p of found.pages) {
      const r = extractContacts(p);
      r.emails.forEach(e => emails.add(e)); r.phones.forEach(t => phones.add(t));
    }
    if (!emails.size) {
      const base = found.url.replace(/\/+$/, '');
      for (const pth of CONTACT_PATHS) {
        const page = await fetchText(base + pth, 6000);
        if (page) {
          const r = extractContacts(page);
          r.emails.forEach(e => emails.add(e)); r.phones.forEach(t => phones.add(t));
          if (emails.size) break;
        }
      }
    }
  }
  // validation MX : on ne livre que des emails dont le domaine accepte du courrier
  const valid = [];
  for (const e of [...emails].slice(0, 6)) if (await mxOK(e)) valid.push(e);

  delete lead.__personne;
  return {
    ...lead,
    site_web: found ? found.url : '',
    site_confiance: found ? found.conf : '',
    emails_publics: valid.slice(0, 3).join(' | '),
    telephones_publics: [...phones].slice(0, 2).join(' | '),
  };
}

// ---------- Main (pool de workers) ----------
async function main() {
  const a = parseArgs(process.argv);
  const input = a._[0];
  if (!input || a.help) {
    console.log('Usage: node enrich.js <leads.csv> [--out fichier.csv] [--max 50] [--concurrence 4] [--sans-ddg]');
    return;
  }
  const max = parseInt(a.max || '50', 10);
  const conc = Math.min(Math.max(parseInt(a.concurrence || '4', 10), 1), 6);
  const out = a.out || input.replace(/\.csv$/i, '') + '-enrichis.csv';
  const useDDG = !a['sans-ddg'];

  const { rows } = parseCSV(fs.readFileSync(input, 'utf8'));
  const todo = rows.slice(0, max);
  console.log(`🔎 Enrichissement de ${todo.length} leads (concurrence ${conc}, DDG ${useDDG ? 'en secours' : 'désactivé'})...`);

  const enriched = new Array(todo.length);
  let done = 0, sites = 0, withEmail = 0, next = 0;

  const LEAD_TIMEOUT = parseInt(process.env.ENRICH_LEAD_TIMEOUT_MS || '120000', 10); // garde-fou : un lead ne bloque jamais la file
  async function worker() {
    while (next < todo.length) {
      const i = next++;
      enriched[i] = await Promise.race([
        enrichOne(todo[i], useDDG),
        sleep(LEAD_TIMEOUT).then(() => ({ ...todo[i], site_web: '', site_confiance: '', emails_publics: '', telephones_publics: '', enrich_erreur: 'timeout' })),
      ]);
      done++;
      if (enriched[i].site_web) sites++;
      if (enriched[i].emails_publics) withEmail++;
      process.stdout.write(`\r   ${done}/${todo.length} traités — ${sites} sites, ${withEmail} avec email   `);
    }
  }
  await Promise.all(Array.from({ length: conc }, worker));
  console.log('');

  // garde les colonnes enrichies même pour les lignes non traitées
  const all = [...enriched, ...rows.slice(max).map(r => ({ ...r, site_web: '', site_confiance: '', emails_publics: '', telephones_publics: '' }))];

  fs.writeFileSync(out, '\ufeff' + toCSV(all));
  const conf = { haute: 0, moyenne: 0, basse: 0 };
  enriched.forEach(e => { if (e.site_confiance) conf[e.site_confiance]++; });
  console.log(`✅ Export → ${out}`);
  console.log(`   Sites : ${sites}/${todo.length} (confiance haute: ${conf.haute}, moyenne: ${conf.moyenne}, basse: ${conf.basse}) — Emails MX-validés : ${withEmail}`);
  if (useDDG && ddgChallenges) console.log(`   ⚠️  DuckDuckGo a renvoyé ${ddgChallenges} page(s) anti-robot (sans résultats) : relance plus tard les leads sans site.`);
}

main().then(() => process.exit(0)).catch(e => { console.error('💥', e.message); process.exit(1); });
