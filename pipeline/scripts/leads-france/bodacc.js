#!/usr/bin/env node
/**
 * BODACC FRESH LEADS v2 — Créations d'entreprises toutes fraîches
 * Source : API BODACC (bodacc-datadila.opendatasoft.com) — officielle, sans clé
 *
 * v2 : endpoint /exports → TOUT en UNE requête (plus de pagination),
 *      types multiples, bornes de dates précises, filtres activité/forme/capital.
 *
 * Les entreprises qui viennent de se créer = les MEILLEURS leads :
 * elles ont besoin de TOUT (site web, logo, communication, compta...).
 *
 * Usage :
 *   node bodacc.js --dept 75 --jours 7 --max 100 --out creations.csv
 *   node bodacc.js --dept 06 --jours 30 --type vente
 *   node bodacc.js --dept 93 --jours 14 --activite "restaur|traiteur|pizz"
 */

const fs = require('fs');
const path = require('path');

const API = 'https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/exports/json';
const TYPES = ['creation', 'immatriculation', 'vente', 'modification', 'radiation', 'collective'];

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
🆕 BODACC FRESH LEADS v2 — Entreprises fraîchement créées (ou en mouvement)

ZONE / PÉRIODE :
  --dept <numéros>    Département(s), ex: 75,92,93
  --ville <nom>       Filtrer par ville (ex: Paris)
  --jours <n>         Annonces des N derniers jours (défaut: 7)
  --depuis <date>     Borne basse précise AAAA-MM-JJ (remplace --jours)
  --jusqua <date>     Borne haute précise AAAA-MM-JJ

TYPE D'ANNONCE :
  --type <types>      ${TYPES.join(' | ')} — combinables (défaut: creation,immatriculation)
                      vente = fonds de commerce vendus → NOUVEAUX PROPRIÉTAIRES
                      collective = procédures collectives (à ÉVITER en prospection)

PRÉCISION :
  --activite <regex>  Ne garde que les activités déclarées qui matchent (ex: "restaur|pizz")
  --forme <regex>     Forme juridique déclarée (ex: "SAS|SARL")
  --capital-min <n>   Capital social minimum en euros (écarte les coquilles vides)

OPTIONS :
  --max <n>           Max résultats (défaut: 500)
  --out <fichier>     Sortie .csv ou .json (défaut: bodacc.csv)

EXEMPLES :
  node bodacc.js --dept 75 --jours 7                          → créations à Paris cette semaine
  node bodacc.js --dept 95 --ville Sarcelles --jours 30
  node bodacc.js --dept 06 --jours 30 --type vente            → fonds de commerce vendus
  node bodacc.js --dept 93 --jours 14 --activite "batiment|maconnerie" --capital-min 1000
`;

const parseJSON = (raw) => { try { return typeof raw === 'string' ? JSON.parse(raw) : raw; } catch { return null; } };
const fmtAdresse = (ad) => ad ? [ad.numeroVoie, ad.typeVoie, ad.nomVoie, ad.codePostal, ad.ville].filter(Boolean).join(' ') : '';

function parsePersonnes(raw) {
  const obj = parseJSON(raw);
  let p = obj?.personne;
  if (Array.isArray(p)) p = p[0];
  if (!p) return {};
  return {
    denomination: p.denomination || [p.prenom, p.nom].filter(Boolean).join(' ') || '',
    enseigne: p.nomCommercial || '',
    forme: p.formeJuridique || '',
    capital: p.capital?.montantCapital || '',
    devise: p.capital?.devise || 'EUR',
    activite: p.activite || '',
    adresse: fmtAdresse(p.adresseSiegeSocial || p.adresseEtablissementPrincipal),
    administration: typeof p.administration === 'string' ? p.administration.slice(0, 300) : '',
  };
}

// L'activité déclarée et l'adresse d'EXPLOITATION vivent dans listeetablissements
// (souvent absentes de listepersonnes, surtout pour les personnes physiques)
function parseEtablissement(raw) {
  const obj = parseJSON(raw);
  let e = obj?.etablissement;
  if (Array.isArray(e)) e = e[0];
  if (!e) return {};
  return {
    activite: e.activite || '',
    adresse: fmtAdresse(e.adresse),
    origine_fonds: e.origineFonds || '',
  };
}

function parseActe(raw) {
  const obj = parseJSON(raw);
  if (!obj) return {};
  return {
    date_immatriculation: obj.dateImmatriculation || '',
    date_debut_activite: obj.dateCommencementActivite || '',
  };
}

function toCSV(rows) {
  if (!rows.length) return '';
  const cols = Object.keys(rows[0]);
  const esc = (v) => { const s = String(v ?? ''); return /[",;\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return [cols.join(';'), ...rows.map(r => cols.map(c => esc(r[c])).join(';'))].join('\n');
}

async function main() {
  const a = parseArgs(process.argv);
  if (a.help) { console.log(HELP); return; }

  const max = Math.min(parseInt(a.max || '500', 10), 50000);
  const out = a.out || 'bodacc.csv';
  const types = String(a.type || 'creation,immatriculation').split(',').map(t => t.trim()).filter(t => TYPES.includes(t));
  if (!types.length) { console.error(`❌ --type invalide. Valeurs : ${TYPES.join(', ')}`); process.exit(1); }

  const depuis = a.depuis || new Date(Date.now() - parseInt(a.jours || '7', 10) * 86400000).toISOString().slice(0, 10);
  const where = [`(${types.map(t => `familleavis="${t}"`).join(' OR ')})`, `dateparution>="${depuis}"`];
  if (a.jusqua) where.push(`dateparution<="${a.jusqua}"`);
  if (a.dept) {
    const depts = String(a.dept).split(',').map(d => `numerodepartement="${d.trim().padStart(2, '0')}"`);
    where.push(`(${depts.join(' OR ')})`);
  }
  if (a.ville) where.push(`ville LIKE "${a.ville}"`);

  console.log(`🆕 BODACC v2 — ${types.join('+')} depuis le ${depuis}${a.jusqua ? ` jusqu'au ${a.jusqua}` : ''}${a.dept ? ` (dept ${a.dept})` : ''}`);

  // v2 : /exports/json = TOUT en une seule requête, pas de pagination
  const p = new URLSearchParams({
    where: where.join(' AND '),
    order_by: 'dateparution DESC',
    limit: String(max),
    select: 'dateparution,familleavis_lib,commercant,ville,cp,numerodepartement,registre,tribunal,listepersonnes,listeetablissements,acte,url_complete',
  });
  const res = await fetch(`${API}?${p}`, { headers: { 'User-Agent': 'leads-france-skill/2.0' } });
  if (!res.ok) { console.error(`💥 HTTP ${res.status}: ${(await res.text()).slice(0, 300)}`); process.exit(1); }
  const results = await res.json();
  console.log(`   📥 ${results.length} annonces reçues (1 seule requête)`);

  const reActivite = a.activite ? new RegExp(a.activite, 'i') : null;
  const reForme = a.forme ? new RegExp(a.forme, 'i') : null;
  const capMin = a['capital-min'] ? parseFloat(a['capital-min']) : null;

  const rows = [];
  for (const r of results) {
    const p2 = parsePersonnes(r.listepersonnes);
    const et = parseEtablissement(r.listeetablissements);
    const ac = parseActe(r.acte);
    const activite = et.activite || p2.activite || '';
    if (reActivite && !reActivite.test(activite)) continue;
    if (reForme && !reForme.test(p2.forme || '')) continue;
    if (capMin !== null && !(parseFloat(p2.capital) >= capMin)) continue;
    const siren = ((r.registre || [])[1] || (r.registre || [])[0] || '').replace(/\s/g, '');
    rows.push({
      date_parution: r.dateparution,
      type: r.familleavis_lib || '',
      denomination: p2.denomination || r.commercant || '',
      enseigne: p2.enseigne,
      forme_juridique: p2.forme,
      capital: p2.capital ? `${p2.capital} ${p2.devise}` : '',
      activite_declaree: activite,
      date_debut_activite: ac.date_debut_activite,
      adresse: et.adresse || p2.adresse,
      ville: r.ville || '',
      cp: r.cp || '',
      departement: r.numerodepartement || '',
      siren,
      annuaire_url: siren ? `https://annuaire-entreprises.data.gouv.fr/entreprise/${siren}` : '',
      annonce_pdf: r.url_complete || '',
      tribunal: r.tribunal || '',
    });
  }

  if (!rows.length) { console.log('❌ Aucune annonce après filtres. Élargis la période ou les filtres.'); return; }

  const ext = path.extname(out).toLowerCase();
  if (ext === '.json') fs.writeFileSync(out, JSON.stringify(rows, null, 2));
  else fs.writeFileSync(out, '\ufeff' + toCSV(rows));
  console.log(`✅ ${rows.length} leads frais exportés → ${out}${rows.length < results.length ? ` (${results.length - rows.length} écartés par les filtres de précision)` : ''}`);
}

main().catch(e => { console.error('💥 Erreur fatale:', e.message); process.exit(1); });
