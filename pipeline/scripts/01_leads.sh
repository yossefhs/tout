#!/usr/bin/env bash
# 01_leads.sh — Composant A du pipeline Clients Ici : collecte SIRENE → enrichissement → file de prospection
#
# Étapes :
#   1. config.json (créé / complété par config_util.py)
#   2. leads.js    : une requête API Recherche d'entreprises par (groupe NAF × département)
#   3. merge_csv.py: fusion + dédoublonnage par SIREN
#   4. enrich.js   : site web vérifié (confiance haute/moyenne/basse) + e-mails MX-validés + téléphones
#   5. filter_queue.py : data/queue.csv (règles RGPD B2B, opposition.csv, ledger.csv)
#
# Usage : scripts/01_leads.sh [options]
#   --groupe artisans|commerces|tous   groupes de NAF de config.json à traiter (défaut : tous)
#   --nafs 43.22A,43.21A               codes NAF explicites (remplace les groupes)
#   --depts 28,27                      départements (défaut : config.depts)
#   --max <n>                          leads max par requête (défaut : config.max_par_requete)
#   --max-enrich <n>                   leads à enrichir (défaut : config.max_enrichissement)
#   --concurrence <n>                  sites consultés en parallèle (défaut : config.concurrence_enrichissement)
#   --avec-ddg | --sans-ddg            secours DuckDuckGo pour trouver le site (défaut : config.utiliser_ddg)
#   --ajouter                          ajoute à data/queue.csv au lieu de la réécrire
#   --depuis-bruts <csv>               saute la collecte, enrichit ce CSV (sortie leads.js / merge_csv.py)
#   --depuis-enrichis <csv>            saute collecte et enrichissement, filtre ce CSV (sortie enrich.js)
#   --help
#
# Aucun envoi, aucune écriture hors de pipeline/data et pipeline/config.json.
set -euo pipefail

ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE="$(dirname "$ICI")"
LF="$ICI/leads-france"
DATA="$PIPELINE/data"
RAW="$DATA/raw"
LOGS="$DATA/logs"
CONFIG="$PIPELINE/config.json"
PY="${PYTHON:-/home/user/.venv-webtest/bin/python}"
command -v "$PY" >/dev/null 2>&1 || PY="$(command -v python3)"
command -v node >/dev/null 2>&1 || { echo "ERREUR : node introuvable" >&2; exit 2; }
export ENRICH_ANNUAIRES="${ENRICH_ANNUAIRES:-$ICI/annuaires.txt}"

GROUPE="tous"; NAFS=""; DEPTS=""; MAX=""; MAX_ENRICH=""; CONC=""; DDG=""; AJOUTER=""; DEPUIS_BRUTS=""; DEPUIS_ENRICHIS=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --groupe) GROUPE="$2"; shift 2;;
    --nafs) NAFS="$2"; shift 2;;
    --depts) DEPTS="$2"; shift 2;;
    --max) MAX="$2"; shift 2;;
    --max-enrich) MAX_ENRICH="$2"; shift 2;;
    --concurrence) CONC="$2"; shift 2;;
    --avec-ddg) DDG="true"; shift;;
    --sans-ddg) DDG="false"; shift;;
    --ajouter) AJOUTER="--ajouter"; shift;;
    --depuis-bruts) DEPUIS_BRUTS="$2"; shift 2;;
    --depuis-enrichis) DEPUIS_ENRICHIS="$2"; shift 2;;
    -h|--help) sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "Option inconnue : $1 (voir --help)" >&2; exit 2;;
  esac
done

mkdir -p "$RAW" "$LOGS"
TS="$(date +%Y%m%d-%H%M%S)"
LOG="$LOGS/01_leads_$TS.log"
RESUME="$LOGS/01_leads_$TS.json"
exec > >(tee -a "$LOG") 2>&1
echo "=== 01_leads.sh — $TS ==="
T0=$(date +%s)

# 1. configuration
"$PY" "$ICI/config_util.py" ensure "$CONFIG"
cfg() { "$PY" "$ICI/config_util.py" get "$1" "$CONFIG"; }
[[ -n "$DEPTS" ]] || DEPTS="$(cfg depts)"
[[ -n "$MAX" ]] || MAX="$(cfg max_par_requete)"
[[ -n "$MAX_ENRICH" ]] || MAX_ENRICH="$(cfg max_enrichissement)"
[[ -n "$CONC" ]] || CONC="$(cfg concurrence_enrichissement)"
[[ -n "$DDG" ]] || DDG="$(cfg utiliser_ddg)"
EXCLURE_EI="$(cfg exclure_ei)"
SIEGE="$(cfg siege_uniquement)"
CATEGORIE="$(cfg categorie)"

declare -a REQUETES=()   # "groupe|nafs"
if [[ -n "$NAFS" ]]; then
  REQUETES+=("perso|$NAFS")
else
  case "$GROUPE" in
    artisans) REQUETES+=("artisans|$(cfg nafs_artisans)");;
    commerces) REQUETES+=("commerces|$(cfg nafs_commerces)");;
    tous) REQUETES+=("artisans|$(cfg nafs_artisans)" "commerces|$(cfg nafs_commerces)");;
    *) echo "ERREUR : --groupe doit valoir artisans, commerces ou tous" >&2; exit 2;;
  esac
fi

ARGS_LEADS=()
[[ "$EXCLURE_EI" == "true" ]] && ARGS_LEADS+=(--exclure-ei)
[[ "$SIEGE" == "true" ]] && ARGS_LEADS+=(--siege)
[[ -n "$CATEGORIE" ]] && ARGS_LEADS+=(--categorie "$CATEGORIE")

BRUTS="$DEPUIS_BRUTS"
ENRICHIS="$DEPUIS_ENRICHIS"
N_REQ=0; N_OK=0; T_COLLECTE=0; T_ENRICH=0

# 2. collecte
if [[ -z "$BRUTS" && -z "$ENRICHIS" ]]; then
  echo "--- Collecte SIRENE (départements : $DEPTS ; max/requête : $MAX ; exclure_ei : $EXCLURE_EI ; siège : $SIEGE ; catégorie : ${CATEGORIE:-toutes})"
  TC0=$(date +%s)
  declare -a FICHIERS=()
  IFS=',' read -ra LISTE_DEPTS <<< "$DEPTS"
  for req in "${REQUETES[@]}"; do
    grp="${req%%|*}"; nafs="${req#*|}"
    for dept in "${LISTE_DEPTS[@]}"; do
      dept="$(echo "$dept" | tr -d ' ')"
      [[ -n "$dept" ]] || continue
      f="$RAW/leads_${grp}_${dept}_$TS.csv"
      N_REQ=$((N_REQ+1))
      echo ">> leads.js --naf $nafs --dept $dept --max $MAX ${ARGS_LEADS[*]:-}"
      if node "$LF/leads.js" --naf "$nafs" --dept "$dept" --max "$MAX" "${ARGS_LEADS[@]}" --out "$f"; then
        if [[ -s "$f" ]]; then FICHIERS+=("$f"); N_OK=$((N_OK+1)); else echo "   (aucun lead pour $grp / $dept)"; fi
      else
        echo "   ⚠️  leads.js a échoué pour $grp / $dept — on continue avec les autres requêtes"
      fi
      sleep 1
    done
  done
  T_COLLECTE=$(( $(date +%s) - TC0 ))
  if [[ ${#FICHIERS[@]} -eq 0 ]]; then
    echo "ERREUR : aucune collecte n'a abouti (API indisponible ? filtres trop étroits ?). Voir $LOG" >&2
    exit 1
  fi
  BRUTS="$RAW/leads_fusion_$TS.csv"
  "$PY" "$ICI/merge_csv.py" "$BRUTS" "${FICHIERS[@]}"
fi

# 3. enrichissement
if [[ -z "$ENRICHIS" ]]; then
  [[ -s "$BRUTS" ]] || { echo "ERREUR : fichier brut absent ou vide : $BRUTS" >&2; exit 1; }
  ENRICHIS="$RAW/enrichis_$TS.csv"
  ARGS_ENRICH=(--max "$MAX_ENRICH" --concurrence "$CONC")
  [[ "$DDG" == "true" ]] || ARGS_ENRICH+=(--sans-ddg)
  echo "--- Enrichissement : enrich.js $(basename "$BRUTS") ${ARGS_ENRICH[*]}"
  TE0=$(date +%s)
  node "$LF/enrich.js" "$BRUTS" "${ARGS_ENRICH[@]}" --out "$ENRICHIS"
  T_ENRICH=$(( $(date +%s) - TE0 ))
fi

# 4. file de prospection
[[ -s "$ENRICHIS" ]] || { echo "ERREUR : fichier enrichi absent ou vide : $ENRICHIS" >&2; exit 1; }
echo "--- Filtrage → $DATA/queue.csv"
STATS_FILE="$LOGS/01_leads_${TS}_filtre.json"
"$PY" "$ICI/filter_queue.py" "$ENRICHIS" --out "$DATA/queue.csv" --data-dir "$DATA" $AJOUTER | tee "$STATS_FILE"

T_TOTAL=$(( $(date +%s) - T0 ))
"$PY" - "$RESUME" "$TS" "$N_REQ" "$N_OK" "$T_COLLECTE" "$T_ENRICH" "$T_TOTAL" "$BRUTS" "$ENRICHIS" "$DDG" "$STATS_FILE" <<'PYEOF'
import json, sys
resume, ts, nreq, nok, tc, te, tt, bruts, enrichis, ddg, stats_file = sys.argv[1:12]
stats = json.load(open(stats_file, encoding="utf-8"))
doc = {"horodatage": ts, "requetes_sirene": int(nreq), "requetes_ok": int(nok),
       "duree_s": {"collecte": int(tc), "enrichissement": int(te), "total": int(tt)},
       "fichiers": {"bruts": bruts, "enrichis": enrichis}, "ddg": ddg == "true", "filtre": stats}
json.dump(doc, open(resume, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"✅ Terminé en {tt}s — file : {stats['sortie']['total_file']} lead(s) ({stats['sortie']['nouvelles']} nouveaux). Résumé : {resume}")
PYEOF
