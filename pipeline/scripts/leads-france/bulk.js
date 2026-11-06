#!/usr/bin/env node
/**
 * BULK v2 — Collectes MASSIVES et ILLIMITÉES sur la base SIRENE complète
 * Moteur : DuckDB + fichiers Parquet officiels INSEE publiés sur data.gouv.fr
 *
 * Contrairement à leads.js (API), AUCUNE limite : pas de plafond 10 000,
 * pas de rate limit, pas de panne 503, et les filtres de DATE et d'EFFECTIF
 * s'appliquent nativement sur les 40M+ d'établissements.
 *
 * Prérequis : DuckDB (brew install duckdb)
 *
 * Modes :
 *  - distant (défaut) : requête directe sur les Parquet de data.gouv (~30-60s/requête)
 *  - --cache : télécharge les Parquet une fois (~3 Go) → requêtes locales en <2s
 *
 * Usage :
 *   node bulk.js --naf 56.10A --dept 95 --cree-apres 2024-01-01 --out resto95.csv
 *   node bulk.js --naf 43.22B --dept 13,83,06 --effectif 03,21 --siege --max 50000
 *   node bulk.js --cache            (télécharge la base pour usage intensif)
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const DATASET_API = 'https://www.data.gouv.fr/api/1/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/';
const CACHE_DIR = path.join(os.homedir(), '.cache', 'leads-france');

function parseArgs(argv) {
  const a = {};
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    if (k.startsWith('--')) {
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) a[k.slice(2)] = true;
      else { a[k.slice(2)] = next; i++; }
    }
  }
  return a;
}

const HELP = `
🏭 BULK v2 — SIRENE complète via DuckDB/Parquet (AUCUNE limite, filtres natifs)

CIBLAGE (tous côté moteur, y compris les DATES) :
  --naf <codes>          Code(s) NAF établissement (ex: 56.10A,56.10B)
  --cp <codes>           Code(s) postal(aux)
  --dept <numéros>       Département(s) (75,92 ou 2A, 971...)
  --commune <codes>      Code(s) commune INSEE
  --cree-apres <date>    Établissements créés après AAAA-MM-JJ
  --cree-avant <date>    Établissements créés avant AAAA-MM-JJ
  --effectif <min,max>   Tranche effectif (codes INSEE, ex: 03,12)
  --forme <codes>        Catégorie juridique (5710=SAS, 5499=SARL...)
  --categorie <cats>     PME, ETI, GE
  --q <texte>            Nom/enseigne contient ce texte (insensible casse)
  --siege                Sièges uniquement
  --avec-effectif        Écarte les tranches vides/NN (coquilles sans salarié déclaré)
  --inclure-nd           Garde les non-diffusibles [ND] (exclus par défaut)

OPTIONS :
  --max <n>              Limite (défaut: 10000 ; mets 1000000 pour tout)
  --out <fichier>        CSV de sortie (défaut: bulk.csv)
  --cache                Télécharge les Parquet en local (~3 Go, requêtes <2s ensuite)
  --sql                  Affiche la requête SQL sans l'exécuter

NOTES :
  - La base est rafraîchie chaque mois sur data.gouv (le script prend toujours la dernière).
  - Dirigeants/finances/labels ne sont PAS dans le stock INSEE → croiser avec leads.js
    (ou enrichir les SIREN obtenus via l'API).
`;

// ---------- Sécurité SQL (valeurs CLI → littéraux sûrs) ----------
const sq = (s) => `'${String(s).replace(/'/g, "''")}'`;
const csvList = (s) => String(s).split(',').map(x => x.trim()).filter(Boolean);
const isDate = (s) => /^\d{4}-\d{2}-\d{2}$/.test(s);

const EFF_ORDER = ['NN', '00', '01', '02', '03', '11', '12', '21', '22', '31', '32', '41', '42', '51', '52', '53'];
function effectifList(spec) {
  const [min, max] = String(spec).split(',');
  const i0 = min ? EFF_ORDER.indexOf(min) : 1;
  const i1 = max ? EFF_ORDER.indexOf(max) : EFF_ORDER.length - 1;
  if (i0 < 0 || i1 < 0 || i0 > i1) return null;
  return EFF_ORDER.slice(Math.max(i0, 1), i1 + 1);
}

// ---------- Découverte des derniers Parquet sur data.gouv ----------
async function discoverParquetURLs() {
  const metaFile = path.join(CACHE_DIR, 'urls.json');
  try {
    const m = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
    if (Date.now() - m.ts < 7 * 86400000) return m; // re-vérifie chaque semaine
  } catch { /* pas de cache */ }
  process.stderr.write('🔭 Recherche des derniers fichiers Parquet SIRENE sur data.gouv...\n');
  const res = await fetch(DATASET_API, { headers: { 'User-Agent': 'leads-france-skill/2.0' } });
  if (!res.ok) throw new Error(`data.gouv HTTP ${res.status}`);
  const d = await res.json();
  const find = (re) => (d.resources || []).find(r => re.test(r.title || '') && r.format === 'parquet')?.url;
  const etab = find(/StockEtablissement\b.*parquet/i) || find(/stocketablissement-parquet/i);
  const ul = find(/StockUniteLegale\b.*parquet/i) || find(/stockunitelegale-parquet/i);
  if (!etab || !ul) throw new Error('Parquet SIRENE introuvables sur data.gouv (structure du dataset modifiée ?)');
  const meta = { ts: Date.now(), etab, ul };
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  fs.writeFileSync(metaFile, JSON.stringify(meta, null, 2));
  return meta;
}

// ---------- Cache local ----------
function localPath(url) { return path.join(CACHE_DIR, path.basename(new URL(url).pathname)); }
function cachedOrRemote(url) {
  const lp = localPath(url);
  return fs.existsSync(lp) ? lp : url;
}
function downloadToCache(url) {
  const lp = localPath(url);
  if (fs.existsSync(lp)) { console.log(`   déjà en cache : ${lp}`); return; }
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  console.log(`⬇️  ${url}\n    → ${lp}`);
  const r = spawnSync('curl', ['-L', '--progress-bar', '-o', lp + '.part', url], { stdio: 'inherit' });
  if (r.status !== 0) { try { fs.unlinkSync(lp + '.part'); } catch {} throw new Error('téléchargement échoué'); }
  fs.renameSync(lp + '.part', lp);
}

// ---------- Construction SQL ----------
function buildSQL(a, etabSrc, ulSrc, max, outTmp) {
  const w = [`e.etatAdministratifEtablissement = 'A'`, `u.etatAdministratifUniteLegale = 'A'`];
  // écarte les non-diffusibles ([ND] : données masquées, interdites de démarchage)
  if (!a['inclure-nd']) w.push(`e.statutDiffusionEtablissement = 'O'`);
  if (a.naf) w.push(`e.activitePrincipaleEtablissement IN (${csvList(a.naf).map(sq).join(',')})`);
  if (a.cp) w.push(`e.codePostalEtablissement IN (${csvList(a.cp).map(sq).join(',')})`);
  if (a.commune) w.push(`e.codeCommuneEtablissement IN (${csvList(a.commune).map(sq).join(',')})`);
  if (a.dept) {
    const conds = csvList(a.dept).map(d => {
      const dd = d.length === 1 ? '0' + d : d;
      return `substr(e.codeCommuneEtablissement, 1, ${dd.length}) = ${sq(dd.toUpperCase())}`;
    });
    w.push(`(${conds.join(' OR ')})`);
  }
  if (a['cree-apres']) { if (!isDate(a['cree-apres'])) throw new Error('--cree-apres : format AAAA-MM-JJ'); w.push(`e.dateCreationEtablissement >= DATE ${sq(a['cree-apres'])}`); }
  if (a['cree-avant']) { if (!isDate(a['cree-avant'])) throw new Error('--cree-avant : format AAAA-MM-JJ'); w.push(`e.dateCreationEtablissement <= DATE ${sq(a['cree-avant'])}`); }
  if (a.effectif) {
    const list = effectifList(a.effectif);
    if (!list) throw new Error(`--effectif invalide (codes : ${EFF_ORDER.slice(1).join(' ')})`);
    w.push(`e.trancheEffectifsEtablissement IN (${list.map(sq).join(',')})`);
  }
  if (a['avec-effectif']) w.push(`e.trancheEffectifsEtablissement IS NOT NULL AND e.trancheEffectifsEtablissement NOT IN ('NN','00')`);
  if (a.siege) w.push(`e.etablissementSiege = true`);
  if (a.forme) w.push(`u.categorieJuridiqueUniteLegale IN (${csvList(a.forme).map(sq).join(',')})`);
  if (a.categorie) w.push(`u.categorieEntreprise IN (${csvList(String(a.categorie).toUpperCase()).map(sq).join(',')})`);
  if (a.q) w.push(`(upper(COALESCE(u.denominationUniteLegale,'') || ' ' || COALESCE(u.nomUniteLegale,'') || ' ' || COALESCE(e.enseigne1Etablissement,'') || ' ' || COALESCE(e.denominationUsuelleEtablissement,'')) LIKE upper(${sq('%' + a.q + '%')}))`);

  return `
INSTALL httpfs; LOAD httpfs;
SET enable_progress_bar=false;
COPY (
  SELECT
    e.siren,
    e.siret,
    COALESCE(u.denominationUniteLegale, trim(concat_ws(' ', u.prenom1UniteLegale, u.nomUniteLegale))) AS nom,
    COALESCE(e.enseigne1Etablissement, e.denominationUsuelleEtablissement, '') AS enseigne,
    e.activitePrincipaleEtablissement AS naf,
    u.categorieJuridiqueUniteLegale AS forme_juridique,
    trim(concat_ws(' ', e.numeroVoieEtablissement, e.typeVoieEtablissement, e.libelleVoieEtablissement)) AS adresse,
    e.codePostalEtablissement AS code_postal,
    e.libelleCommuneEtablissement AS ville,
    e.dateCreationEtablissement AS date_creation,
    e.trancheEffectifsEtablissement AS effectif,
    u.trancheEffectifsUniteLegale AS effectif_entreprise,
    u.categorieEntreprise AS categorie,
    u.dateCreationUniteLegale AS date_creation_entreprise,
    CASE WHEN e.etablissementSiege THEN 'oui' ELSE '' END AS est_siege,
    'https://annuaire-entreprises.data.gouv.fr/entreprise/' || e.siren AS annuaire_url
  FROM read_parquet(${sq(etabSrc)}) e
  JOIN read_parquet(${sq(ulSrc)}) u USING (siren)
  WHERE ${w.join('\n    AND ')}
  ORDER BY e.dateCreationEtablissement DESC
  LIMIT ${max}
) TO ${sq(outTmp)} (HEADER, DELIMITER ';');
`;
}

// ---------- Main ----------
async function main() {
  const a = parseArgs(process.argv);
  if (a.help || Object.keys(a).length === 0) { console.log(HELP); return; }

  // DuckDB présent ?
  if (spawnSync('duckdb', ['--version']).status !== 0) {
    console.error('❌ DuckDB introuvable. Installe-le : brew install duckdb');
    process.exit(1);
  }

  const urls = await discoverParquetURLs();

  if (a.cache) {
    console.log('📦 Mise en cache locale des Parquet SIRENE (~3 Go)...');
    downloadToCache(urls.etab);
    downloadToCache(urls.ul);
    console.log('✅ Cache prêt. Toutes les prochaines requêtes bulk.js seront locales (<2s).');
    if (!a.naf && !a.cp && !a.dept && !a.q) return;
  }

  const etabSrc = cachedOrRemote(urls.etab);
  const ulSrc = cachedOrRemote(urls.ul);
  const remote = etabSrc.startsWith('http');
  const max = Math.min(parseInt(a.max || '10000', 10), 5000000);
  const out = a.out || 'bulk.csv';
  const outTmp = out + '.tmp';

  const sql = buildSQL(a, etabSrc, ulSrc, max, outTmp);
  if (a.sql) { console.log(sql); return; }

  console.log(`🏭 BULK — SIRENE complète (${remote ? 'distant : compte 30-60s, --cache pour accélérer' : 'cache local'})`);
  const t0 = Date.now();
  const r = spawnSync('duckdb', ['-c', sql], { encoding: 'utf8' });
  if (r.status !== 0) {
    console.error('💥 DuckDB :', (r.stderr || r.stdout || '').slice(0, 600));
    process.exit(1);
  }

  // BOM UTF-8 pour Excel
  const csv = fs.readFileSync(outTmp, 'utf8');
  fs.unlinkSync(outTmp);
  fs.writeFileSync(out, '\ufeff' + csv);
  const n = csv.trim().split('\n').length - 1;
  console.log(`✅ ${n} établissements exportés → ${out} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
}

main().catch(e => { console.error('💥 Erreur fatale:', e.message); process.exit(1); });
