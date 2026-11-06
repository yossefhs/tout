#!/usr/bin/env node
/**
 * LEADS FRANCE v2 — Robot de génération de leads B2B
 * Source : API Recherche d'entreprises (recherche-entreprises.api.gouv.fr)
 * Données officielles SIRENE/INSEE + RNE — sans clé API, 100% légal (open data)
 *
 * v2 : filtres serveur (effectif, catégorie, commune, epci, dirigeant, convention),
 *      réponses minimales (minimal+include), pages parallèles, ciblage par rayon
 *      (/near_point), exclusions, adresse de l'établissement matché, NAF 2025,
 *      score de qualification, auto-découpage au-delà du plafond de 10 000.
 *
 * Usage :
 *   node leads.js --naf 62.01Z --dept 75 --max 200 --out leads.csv
 *   node leads.js --autour "48.8841,2.3781" --rayon 3 --naf 56.10A
 *   node leads.js --help
 */

const fs = require('fs');
const path = require('path');

const API = 'https://recherche-entreprises.api.gouv.fr';
const PER_PAGE = 25;          // max autorisé par l'API
const MAX_RETRIES = 7;
const HARD_CAP_PAGES = 400;   // l'API plafonne à 10 000 résultats (400 × 25) par requête

// ---------- CLI ----------
function parseArgs(argv) {
  const a = {};
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith('--')) {
      const key = k.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) { a[key] = true; }
      else { a[key] = next; i++; }
    }
  }
  return a;
}

const HELP = `
🤖 LEADS FRANCE v2 — Robot officiel (SIRENE / data.gouv.fr)

CIBLAGE PRINCIPAL :
  --q <texte>            Recherche libre (nom, enseigne, dirigeant)
  --naf <codes>          Code(s) NAF/APE, séparés par virgule (ex: 62.01Z,62.02A)
  --section <lettres>    Section NAF entière (A..U, ex: F = construction)
  --cp <codes>           Code(s) postal(aux) (ex: 75011,75019)
  --commune <codes>      Code(s) commune INSEE (plus fiable qu'un nom de ville)
  --dept <numéros>       Département(s) (ex: 75,92,93)
  --region <codes>       Code(s) région INSEE (ex: 11 = Île-de-France)
  --epci <codes>         Intercommunalité(s) (code EPCI)
  --autour <lat,long>    Ciblage par rayon autour d'un point GPS
  --rayon <km>           Rayon en km (défaut 5, max 50) — avec --autour

PROFIL D'ENTREPRISE :
  --effectif <min,max>   Tranche effectif INSEE, filtrée CÔTÉ SERVEUR (ex: 03,12 = 6 à 49 salariés)
  --categorie <cats>     PME, ETI, GE (ex: --categorie PME,ETI)
  --forme <codes>        Nature juridique (ex: 5710 = SAS, 5499 = SARL)
  --cree-apres <date>    Créées après AAAA-MM-JJ (jeunes entreprises)
  --cree-avant <date>    Créées avant AAAA-MM-JJ
  --ca-min / --ca-max    Chiffre d'affaires (euros)
  --resultat-min / --resultat-max  Résultat net (euros)
  --convention <idcc>    Convention collective (ex: 1596 = bâtiment ouvriers)

PAR DIRIGEANT :
  --dirigeant-nom <nom>      Nom d'un dirigeant ou élu
  --dirigeant-prenom <pren>  Prénom(s) d'un dirigeant ou élu

LABELS / SEGMENTS :
  --rge --bio --ess --qualiopi --association --ei
  --siae                 Insertion par l'activité économique
  --of                   Organismes de formation
  --patrimoine-vivant    Label Entreprise du Patrimoine Vivant
  --societe-mission      Sociétés à mission
  --alim-confiance       Contrôles sanitaires Alim'Confiance (résto/alim)
  --spectacle            Entrepreneurs du spectacle
  --finess               Santé / médico-social (FINESS)
  --egapro               Index égalité pro renseigné
  --achats-responsables  Label RFAR

EXCLUSIONS (précision) :
  --exclure-naf <codes>  Écarte ces codes NAF (préfixe accepté: 47 = tout le commerce de détail)
  --exclure-cp <codes>   Écarte ces codes postaux
  --exclure-ei           Écarte les entrepreneurs individuels / micro
  --employeur            Ne garde que les entreprises employeuses (≥1 salarié déclaré)

OPTIONS :
  --max <n>              Nombre max de leads (défaut 100 ; >10 000 → découpage auto)
  --siege                Sièges sociaux uniquement (sinon: tout établissement dans la zone)
  --tri score            Trie le CSV par score de qualification décroissant
  --parallele <n>        Pages chargées en parallèle (défaut 3, max 5)
  --out <fichier>        Sortie .csv ou .json (défaut: leads.csv)
  --help                 Cette aide

EXEMPLES :
  node leads.js --naf 62.01Z --dept 75 --effectif 03,12 --max 500
  node leads.js --naf 56.10A --cp 75019 --cree-apres 2024-01-01 --tri score
  node leads.js --autour "48.8841,2.3781" --rayon 2 --naf 56.10A --max 100
  node leads.js --rge --dept 13 --exclure-ei --employeur --max 400
  node leads.js --dirigeant-nom Cohen --dept 75 --max 50
`;

// ---------- HTTP avec retry ----------
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function fetchJSON(url, attempt = 1) {
  try {
    const res = await fetch(url, { headers: { 'User-Agent': 'leads-france-skill/2.0' } });
    if (res.status === 429 || res.status >= 500) throw new Error(`HTTP ${res.status}`);
    if (!res.ok) {
      const body = await res.text();
      throw Object.assign(new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`), { fatal: res.status === 400 });
    }
    return await res.json();
  } catch (e) {
    if (e.fatal || attempt >= MAX_RETRIES) throw e;
    const wait = Math.min(1500 * Math.pow(1.8, attempt), 20000) + Math.random() * 500;
    process.stderr.write(`  ⚠️  ${e.message} — retry ${attempt}/${MAX_RETRIES} dans ${Math.round(wait / 1000)}s\n`);
    await sleep(wait);
    return fetchJSON(url, attempt + 1);
  }
}

// ---------- Tranches effectif INSEE ----------
const EFF_ORDER = ['NN', '00', '01', '02', '03', '11', '12', '21', '22', '31', '32', '41', '42', '51', '52', '53'];
// '--effectif min,max' → liste explicite de codes, passée au SERVEUR (v2)
function effectifCodes(spec) {
  const [min, max] = String(spec).split(',');
  const i0 = min ? EFF_ORDER.indexOf(min) : 1;
  const i1 = max ? EFF_ORDER.indexOf(max) : EFF_ORDER.length - 1;
  if (i0 < 0 || i1 < 0 || i0 > i1) return null;
  return EFF_ORDER.slice(Math.max(i0, 1), i1 + 1).join(',');
}

// ---------- Labels booléens ----------
const LABELS = {
  rge: 'est_rge', bio: 'est_bio', ess: 'est_ess', qualiopi: 'est_qualiopi',
  association: 'est_association', ei: 'est_entrepreneur_individuel',
  siae: 'est_siae', of: 'est_organisme_formation',
  'patrimoine-vivant': 'est_patrimoine_vivant', 'societe-mission': 'est_societe_mission',
  'alim-confiance': 'est_alim_confiance', spectacle: 'est_entrepreneur_spectacle',
  finess: 'est_finess', egapro: 'egapro_renseignee', 'achats-responsables': 'est_achats_responsables',
};

// ---------- Construction de la requête ----------
function hasGeoFilter(a) { return !!(a.cp || a.dept || a.region || a.commune || a.epci); }

function buildParams(a) {
  const p = new URLSearchParams();
  if (a.q) p.set('q', a.q);
  if (a.naf) p.set('activite_principale', a.naf);
  if (a.section) p.set('section_activite_principale', String(a.section).toUpperCase());
  if (a.cp) p.set('code_postal', a.cp);
  if (a.commune) p.set('code_commune', a.commune);
  if (a.dept) p.set('departement', a.dept);
  if (a.region) p.set('region', a.region);
  if (a.epci) p.set('epci', a.epci);
  if (a.forme) p.set('nature_juridique', a.forme);
  if (a.categorie) p.set('categorie_entreprise', String(a.categorie).toUpperCase());
  if (a.convention) p.set('id_convention_collective', a.convention);
  if (a['dirigeant-nom']) p.set('nom_personne', a['dirigeant-nom']);
  if (a['dirigeant-prenom']) p.set('prenoms_personne', a['dirigeant-prenom']);
  if (a['ca-min']) p.set('ca_min', a['ca-min']);
  if (a['ca-max']) p.set('ca_max', a['ca-max']);
  if (a['resultat-min']) p.set('resultat_net_min', a['resultat-min']);
  if (a['resultat-max']) p.set('resultat_net_max', a['resultat-max']);
  if (a.effectif) {
    const codes = effectifCodes(a.effectif);
    if (!codes) { console.error(`❌ --effectif invalide : "${a.effectif}" (codes attendus : ${EFF_ORDER.slice(1).join(' ')})`); process.exit(1); }
    p.set('tranche_effectif_salarie', codes); // v2 : filtré côté serveur
  }
  for (const [flag, param] of Object.entries(LABELS)) if (a[flag]) p.set(param, 'true');
  p.set('etat_administratif', 'A'); // entreprises ACTIVES uniquement
  // v2 : réponse minimale — on ne demande que les sections utiles (payload ÷3)
  p.set('minimal', 'true');
  let include = 'siege,complements,dirigeants,finances';
  if (hasGeoFilter(a) && !a.siege) {
    include += ',matching_etablissements'; // l'établissement qui matche VRAIMENT la zone
    p.set('limite_matching_etablissements', '1');
  }
  p.set('include', include);
  p.set('per_page', String(PER_PAGE));
  return p;
}

// ---------- Filtrage côté client (uniquement ce que l'API ne sait pas faire) ----------
function clientFilter(r, a) {
  if (a['cree-apres'] && (!r.date_creation || r.date_creation < a['cree-apres'])) return false;
  if (a['cree-avant'] && (!r.date_creation || r.date_creation > a['cree-avant'])) return false;
  if (a['exclure-naf']) {
    const naf = r.activite_principale || '';
    if (String(a['exclure-naf']).split(',').some(x => naf.startsWith(x.trim()))) return false;
  }
  if (a['exclure-ei'] && (r.nature_juridique === '1000' || r.complements?.est_entrepreneur_individuel)) return false;
  // caractere_employeur n'est plus alimenté par l'INSEE (gelé) → on se base sur la tranche d'effectif
  if (a.employeur && EFF_ORDER.indexOf(r.tranche_effectif_salarie || 'NN') < EFF_ORDER.indexOf('01')) return false;
  if (a['exclure-cp']) {
    const excl = String(a['exclure-cp']).split(',').map(c => c.trim());
    const cpCible = a.siege ? r.siege?.code_postal : (r.matching_etablissements?.[0]?.code_postal || r.siege?.code_postal);
    if (excl.includes(String(cpCible))) return false;
  }
  return true;
}

// ---------- Score de qualification (0–100) ----------
function scoreLead(r) {
  let s = 0;
  if (r.date_creation) {
    const age = (Date.now() - new Date(r.date_creation)) / (365.25 * 86400000);
    if (age <= 1) s += 25; else if (age <= 3) s += 15; else if (age <= 10) s += 5;
  }
  const effIdx = EFF_ORDER.indexOf(r.tranche_effectif_salarie || 'NN');
  if (effIdx >= EFF_ORDER.indexOf('12')) s += 15;        // 20+ salariés
  else if (effIdx >= EFF_ORDER.indexOf('03')) s += 10;   // 6-19 salariés
  else if (effIdx >= EFF_ORDER.indexOf('01')) s += 5;    // 1-5 salariés
  const fin = r.finances ? Object.values(r.finances)[0] || {} : {};
  if (fin.ca >= 2000000) s += 15; else if (fin.ca >= 500000) s += 10; else if (fin.ca >= 100000) s += 5;
  const c = r.complements || {};
  if (c.est_rge || c.est_bio || c.est_qualiopi || c.est_ess || c.est_patrimoine_vivant || c.est_organisme_formation) s += 10;
  if ((r.dirigeants || []).length) s += 5;
  if ((r.nombre_etablissements_ouverts || 0) > 1) s += 5;
  return Math.min(s, 100);
}

// ---------- Aplatir un résultat en lead ----------
function toLead(r, a) {
  const s = r.siege || {};
  const m = (r.matching_etablissements || [])[0] || null;
  const dirigeants = (r.dirigeants || []).map(d =>
    d.type_dirigeant === 'personne morale'
      ? `${d.denomination || ''} (${d.qualite || ''})`
      : `${d.prenoms || ''} ${d.nom || ''} (${d.qualite || ''})`
  ).join(' | ');
  const fin = r.finances ? Object.values(r.finances)[0] || {} : {};
  const lead = {
    siren: r.siren,
    siret_siege: s.siret || '',
    nom: r.nom_complet || r.nom_raison_sociale || '',
    enseigne: s.nom_commercial || (s.liste_enseignes || []).join(', ') || '',
    naf: r.activite_principale || '',
    naf_2025: r.activite_principale_naf25 || '',
    forme_juridique: r.nature_juridique || '',
    adresse: s.adresse || '',
    code_postal: s.code_postal || '',
    ville: s.libelle_commune || '',
    departement: s.departement || '',
    latitude: s.latitude || '',
    longitude: s.longitude || '',
    date_creation: r.date_creation || '',
    effectif: r.tranche_effectif_salarie || '',
    categorie: r.categorie_entreprise || '',
    employeur: EFF_ORDER.indexOf(r.tranche_effectif_salarie || 'NN') >= EFF_ORDER.indexOf('01') ? 'oui' : '',
    dirigeants,
    ca: fin.ca || '',
    resultat_net: fin.resultat_net || '',
    nb_etablissements: r.nombre_etablissements_ouverts || '',
    est_rge: r.complements?.est_rge ? 'oui' : '',
    est_bio: r.complements?.est_bio ? 'oui' : '',
    est_ess: r.complements?.est_ess ? 'oui' : '',
    est_qualiopi: r.complements?.est_qualiopi ? 'oui' : '',
    score_lead: scoreLead(r),
    annuaire_url: `https://annuaire-entreprises.data.gouv.fr/entreprise/${r.siren}`,
  };
  // Précision : l'adresse de l'établissement qui matche la ZONE demandée
  // (le siège peut être ailleurs — c'est l'établissement local qu'on démarche)
  if (m && (hasGeoFilter(a) || a.autour) && !a.siege) {
    lead.etab_zone_siret = m.siret || '';
    lead.etab_zone_adresse = m.adresse || '';
    lead.etab_zone_cp = m.code_postal || '';
    lead.etab_zone_ville = m.libelle_commune || '';
  }
  return lead;
}

// ---------- Export ----------
function toCSV(rows) {
  if (!rows.length) return '';
  const cols = [...new Set(rows.flatMap(r => Object.keys(r)))];
  const esc = (v) => {
    const str = String(v ?? '');
    return /[",;\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
  };
  return [cols.join(';'), ...rows.map(r => cols.map(c => esc(r[c])).join(';'))].join('\n');
}

// ---------- Collecte d'une requête (pages en parallèle) ----------
async function collectQuery(baseUrl, params, a, max, sink, conc) {
  params.set('page', '1');
  let data;
  try { data = await fetchJSON(`${baseUrl}?${params}`); }
  catch (e) { console.error(`\n⚠️  API indisponible (${e.message})`); return 0; }
  const totalResults = data.total_results || 0;
  const totalPages = Math.min(data.total_pages || 1, HARD_CAP_PAGES);
  ingest(data.results, a, max, sink);

  let page = 2;
  while (sink.leads.length < max && page <= totalPages) {
    // v2 : vague de `conc` pages en parallèle (limite API : 7 req/s, on reste sous ~5)
    const wave = [];
    for (let i = 0; i < conc && page + i <= totalPages; i++) {
      const p = new URLSearchParams(params); p.set('page', String(page + i));
      wave.push(fetchJSON(`${baseUrl}?${p}`).catch(e => ({ __err: e.message })));
    }
    const results = await Promise.all(wave);
    for (const d of results) {
      if (d.__err) { console.error(`\n⚠️  page perdue (${d.__err}) — on continue.`); continue; }
      ingest(d.results, a, max, sink);
    }
    page += wave.length;
    process.stdout.write(`\r   📥 ${sink.leads.length} leads (page ${Math.min(page - 1, totalPages)}/${totalPages}, dispo: ${totalResults})   `);
    if (sink.leads.length < max && page <= totalPages) await sleep(600);
  }
  return totalResults;
}

function ingest(results, a, max, sink) {
  for (const r of results || []) {
    if (sink.leads.length >= max) return;
    if (sink.seen.has(r.siren)) continue;
    sink.seen.add(r.siren);
    if (!clientFilter(r, a)) continue;
    if (a.siege) {
      const s = r.siege || {};
      if (a.dept && !String(a.dept).split(',').map(d => d.trim().padStart(2, '0')).includes(String(s.departement))) continue;
      if (a.cp && !String(a.cp).split(',').map(c => c.trim()).includes(String(s.code_postal))) continue;
      if (a.commune && !String(a.commune).split(',').map(c => c.trim()).includes(String(s.commune))) continue;
    }
    sink.leads.push(toLead(r, a));
  }
}

// ---------- Main ----------
async function main() {
  const a = parseArgs(process.argv);
  if (a.help || Object.keys(a).length === 0) { console.log(HELP); return; }

  const max = Math.min(parseInt(a.max || '100', 10), 100000);
  const out = a.out || 'leads.csv';
  const conc = Math.min(Math.max(parseInt(a.parallele || '3', 10), 1), 5);
  const sink = { leads: [], seen: new Set() };

  console.log('🤖 LEADS FRANCE v2 — démarrage');

  let totalResults = 0;

  if (a.autour) {
    // ---- Mode rayon GPS (/near_point) ----
    const [lat, long] = String(a.autour).split(',').map(x => x.trim());
    const radius = Math.min(parseFloat(a.rayon || '5'), 50);
    const p = new URLSearchParams({ lat, long, radius: String(radius), per_page: String(PER_PAGE) });
    if (a.naf) p.set('activite_principale', a.naf);
    if (a.section) p.set('section_activite_principale', String(a.section).toUpperCase());
    p.set('minimal', 'true');
    p.set('include', 'siege,complements,dirigeants,finances,matching_etablissements');
    p.set('limite_matching_etablissements', '1');
    console.log(`   🎯 Rayon ${radius} km autour de (${lat}, ${long})`);
    totalResults = await collectQuery(`${API}/near_point`, p, a, max, sink, conc);
  } else {
    // ---- Mode recherche standard, avec auto-découpage si > 10 000 ----
    const params = buildParams(a);
    console.log(`   Filtres : ${decodeURIComponent(params.toString())}`);

    // sonde : combien de résultats au total ?
    const probe = new URLSearchParams(params); probe.set('page', '1'); probe.set('per_page', '1');
    let total = 0;
    try { total = (await fetchJSON(`${API}/search?${probe}`)).total_results || 0; } catch { /* on tentera quand même */ }

    // dimension de découpage : cp > dept > naf (la plus fine d'abord)
    const shardDim = ['cp', 'dept', 'naf'].find(d => a[d] && String(a[d]).includes(','));
    if (total > 10000 && shardDim) {
      const values = String(a[shardDim]).split(',').map(v => v.trim());
      console.log(`   ✂️  ${total} résultats > plafond API (10 000) → découpage par --${shardDim} (${values.length} requêtes)`);
      const apiKey = { cp: 'code_postal', dept: 'departement', naf: 'activite_principale' }[shardDim];
      for (const v of values) {
        if (sink.leads.length >= max) break;
        const p = new URLSearchParams(params); p.set(apiKey, v);
        console.log(`\n   — ${shardDim} ${v} :`);
        await collectQuery(`${API}/search`, p, a, max, sink, conc);
      }
      totalResults = total;
    } else {
      if (total > 10000) console.log(`   ⚠️  ${total} résultats, seuls les 10 000 premiers sont accessibles par l'API.\n      Pour TOUT récupérer : découpe en plusieurs --cp/--dept, ou utilise bulk.js (illimité).`);
      totalResults = await collectQuery(`${API}/search`, params, a, max, sink, conc);
    }
  }
  console.log('');

  let leads = sink.leads;
  if (!leads.length) {
    console.log('❌ Aucun résultat. Élargis tes filtres (voir --help).');
    return;
  }
  if (a.tri === 'score') leads = leads.sort((x, y) => y.score_lead - x.score_lead);

  const ext = path.extname(out).toLowerCase();
  if (ext === '.json') fs.writeFileSync(out, JSON.stringify(leads, null, 2));
  else fs.writeFileSync(out, '\ufeff' + toCSV(leads)); // BOM pour Excel
  console.log(`✅ ${leads.length} leads exportés → ${out}`);
  console.log(`   (${totalResults} entreprises correspondent au total aux filtres serveur)`);
}

main().catch(e => { console.error('💥 Erreur fatale:', e.message); process.exit(1); });
