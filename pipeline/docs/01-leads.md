# Composant A — Leads (collecte, enrichissement, file de prospection)

Chaîne : `scripts/01_leads.sh` → `leads.js` (SIRENE) → `merge_csv.py` → `enrich.js` (site + contacts) → `filter_queue.py` → `data/queue.csv`.
Aucun envoi d'e-mail, aucune écriture hors de `pipeline/data/` et `pipeline/config.json`.

## 1. Sources de données

| Source | Usage | Accès | Fraîcheur |
|---|---|---|---|
| **API Recherche d'entreprises** (`recherche-entreprises.api.gouv.fr`, DINUM) | `leads.js` : entreprises actives par code NAF × département, siège, dirigeants (RNE), effectif, catégorie, labels, score | Open data, sans clé, ~7 req/s max ; 25 résultats/page, plafond 10 000/requête | SIRENE/INSEE quotidien, RNE |
| **Sites des entreprises** (lecture seule) | `enrich.js` : page d'accueil, `/mentions-legales`, pages contact → vérification du site (SIREN, nom + ville), e-mails, téléphones | HTTP GET, User-Agent `Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/)`, ≤ 8 requêtes HTML par site, timeouts 6–8 s | temps réel |
| **DuckDuckGo HTML** (`html.duckduckgo.com`) | `enrich.js` : secours pour trouver le site quand la devinette de domaine (`nom.fr`, `enseigne.fr`…) échoue | 1 requête / 1,5 s, sérialisée ; renvoie parfois une page anti-robot (aucun résultat, le lead reste « sans site ») | temps réel |
| **DNS MX** (natif, puis DNS-over-HTTPS `dns.google` / `cloudflare-dns.com` en secours) | `enrich.js` : un e-mail n'est livré que si son domaine accepte du courrier | — | temps réel |
| `scripts/annuaires.txt` | liste éditable des annuaires/plateformes qui ne sont jamais « le site de l'entreprise » | fichier local | à maintenir |

Jamais utilisés : LinkedIn, Google Maps, Pages Jaunes, formulaires, espaces d'administration (interdits par les règles du projet et les CGU de ces services).

## 2. Cadre RGPD (B2B, intérêt légitime)

Règles reprises du skill `leads-france` et appliquées par le filtre :

- On ne collecte que des **coordonnées professionnelles rendues publiques par l'entreprise elle-même** (son site, ses mentions légales). Base légale : intérêt légitime (art. 6.1.f RGPD) pour la prospection B2B ; information et droit d'opposition dans chaque message (la page d'atterrissage le dit déjà : « répondez STOP »).
- `data/opposition.csv` (`valeur;type;date;source`, type ∈ `email|domaine|siren`) est la **liste d'opposition** : tout ce qui y figure est exclu définitivement de la file, à chaque exécution. À alimenter dès qu'un prospect répond STOP ou demande la suppression.
- `data/ledger.csv` (`date;siren;domaine;email;statut;thread_id;draft_id;maquette_url;notes`) est le **registre des contacts déjà traités** : un domaine, e-mail ou SIREN présent n'est jamais remis en file (pas de double sollicitation).
- Les adresses sur **webmail** (orange.fr, gmail.com, free.fr, wanadoo.fr, sfr.fr, laposte.net…) sont **conservées** : c'est l'adresse professionnelle de la plupart des TPE. Elles sont marquées `email_type=webmail`. Seules sont écartées les adresses **manifestement personnelles** : webmail + partie locale qui est un nom de personne sans rapport avec le nom de l'entreprise (`marie.martin@orange.fr` pour « SARL DUPONT »). `jean.dupont@gmail.com` pour « DUPONT PLOMBERIE » est gardée (c'est l'adresse de l'entreprise). Les adresses nominatives sur le domaine de l'entreprise (`p.martin@chauffage-28.fr`) sont gardées, `email_type=nominatif`.
- Les e-mails de **tiers** présents sur la page (hébergeur, agence web, assureur, annuaire) et les adresses **factices** (`votre@email.com`, `marie.dupont@email.fr`) sont écartés : seul un e-mail du domaine du site, d'un webmail, ou d'un domaine portant le nom de l'entreprise est retenu.
- Données de dirigeants : nom et fonction issus du RNE (données publiques), conservés uniquement pour personnaliser l'e-mail. Pas de date de naissance, pas d'adresse personnelle.
- Conservation : les fichiers `data/raw/*` sont des extractions brutes horodatées ; les purger après exploitation (suggestion : 90 jours).

## 3. Codes NAF retenus (`config.json`)

Libellés officiels NAF rév. 2 (INSEE). Le filtre les écrit dans `libelle_naf` à partir de `scripts/naf_libelles.json`.

**`nafs_artisans`** (bâtiment, cible principale) :

| Code | Libellé officiel | Note |
|---|---|---|
| 43.22A | Travaux d'installation d'eau et de gaz en tous locaux | plombiers |
| 43.22B | Travaux d'installation d'équipements thermiques et de climatisation | chauffagistes, clim, PAC |
| 43.21A | Travaux d'installation électrique dans tous locaux | électriciens |
| 43.32A | Travaux de menuiserie bois et PVC | menuisiers |
| 43.34Z | Travaux de peinture et vitrerie | peintres |
| 43.91A | Travaux de charpente | **attention** : `naf-codes.md` du skill l'annonce « couverture » ; la couverture est **43.91B** (Travaux de couverture par éléments). Voir « À décider ». |
| 43.99C | Travaux de maçonnerie générale et gros œuvre de bâtiment | maçons |

**`nafs_commerces`** (commerces et services de proximité) :

| Code | Libellé officiel | Note |
|---|---|---|
| 96.02A | Coiffure | salons |
| 10.71C | Boulangerie et boulangerie-pâtisserie | fabrication artisanale |
| 47.24Z | Commerce de détail de pain, pâtisserie et confiserie en magasin spécialisé | dépôts de pain, terminaux de cuisson |
| 56.10A | Restauration traditionnelle | restaurants |

Candidats non retenus mais prêts dans `naf_libelles.json` : 43.91B couverture, 43.29A isolation, 43.31Z plâtrerie, 43.33Z carrelage, 43.32B serrurerie, 81.30Z paysagistes, 45.20A garages, 96.02B soins de beauté, 56.10C restauration rapide, 47.22Z boucheries, 75.00Z vétérinaires.

## 4. Paramètres (`config.json`)

| Clé | Défaut | Rôle |
|---|---|---|
| `depts` | `["28"]` | départements (siège). Voisins du 28 : 27, 61, 72, 41, 45, 91, 78 |
| `nafs_artisans`, `nafs_commerces` | voir ci-dessus | une requête API par (groupe × département) |
| `max_par_requete` | 100 | leads collectés par requête (la pagination s'arrête là) |
| `exclure_ei` | false | `true` écarte les entrepreneurs individuels (ils sont majoritaires chez les artisans : à garder) |
| `siege_uniquement` | true | siège dans le département. **Indispensable** : sans cela l'API renvoie les groupes nationaux ayant une agence dans le 28 (SPIE, Eiffage, Equans…) |
| `categorie` | `"PME"` | filtre serveur : écarte ETI et grandes entreprises |
| `max_enrichissement` | 60 | leads enrichis par exécution (le reste est écrit non enrichi dans `data/raw/enrichis_*.csv`) |
| `concurrence_enrichissement` | 3 | sites consultés en parallèle |
| `utiliser_ddg` | true | secours DuckDuckGo (voir limites) |
| `cible_tpe` | `{"effectif_max_code": "11", "ca_max": 2000000, "nb_etablissements_max": 2, "motifs_exclus_nom": ["GROUPE", "HOLDING", "SAS INTERNATIONAL"]}` | cible TPE appliquée par `filter_queue.py` (règle 0 du § 5) : tranche d'effectif INSEE au plus `11` (10 à 19 salariés ; codes `00` 0, `01` 1–2, `02` 3–5, `03` 6–9, `11` 10–19, `12` 20–49, `21` 50–99, `22` 100–199…), CA (dernier exercice publié) ≤ 2 M€, au plus 2 établissements ouverts, aucun des motifs (mots entiers) dans le nom ou l'enseigne. Un champ vide ou `NN` ne fait jamais rejeter. Ajoutée par `config_util.py ensure` si absente ; `filter_queue.py --config <chemin>` pour un autre fichier |

Options de ligne de commande (`scripts/01_leads.sh --help`) : `--groupe`, `--nafs`, `--depts`, `--max`, `--max-enrich`, `--concurrence`, `--avec-ddg|--sans-ddg`, `--ajouter`, `--depuis-bruts <csv>`, `--depuis-enrichis <csv>`.

## 5. Règles du filtre (`filter_queue.py`)

Entrée : CSV `enrich.js`. Sortie : `data/queue.csv` (`;`, UTF-8 BOM) avec les colonnes
`siren;nom;enseigne;naf;libelle_naf;adresse;cp;ville;dept;dirigeants;site;site_confiance;email;email_type;tel;score_lead;date_collecte`, triée par `score_lead` décroissant.

0. **cible TPE** (`config.cible_tpe`, voir § 4) : effectif, CA, nombre d'établissements ouverts et motifs du nom ; motif de rejet `hors_cible_taille:<détail>` (ex. `hors_cible_taille:effectif=22,ca=47311065,nb_etablissements=3,nom~GROUPE`). Appliquée avant tout le reste, donc aussi aux leads « sans site » : la liste des rejets `sans_site` ne contient que des TPE ;
1. site présent **et** domaine hors `annuaires.txt` ;
2. `site_confiance` ∈ {haute, moyenne} (`basse` = premier résultat de recherche non vérifié : écarté) ;
3. au moins un e-mail MX-validé, non factice, non tiers, non personnel ; choix : domaine du site > générique > nominatif > webmail ;
4. exclusion `opposition.csv` + `ledger.csv` (domaine, e-mail, SIREN) ;
5. un seul lead par domaine (meilleur score, puis meilleure confiance).

Chaque lead écarté est tracé dans `data/queue_rejets.csv` avec son motif ; le résumé JSON de chaque exécution est dans `data/logs/01_leads_<horodatage>.json`.

Niveaux de confiance du site (`enrich.js`) : **haute** = SIREN sur le site, ou nom distinctif (≥ 2 mots, ou enseigne entière) **et** ville/code postal ; **moyenne** = nom distinctif sans la ville ; les mots de métier (« électricité », « services »…) ne comptent pas. Un entrepreneur individuel sans enseigne (nom = une personne, homonymes fréquents) n'est accepté qu'en confiance haute.

## 6. Volumes, rendements et durées mesurés (Eure-et-Loir, 5 novembre 2026)

Tout a été mesuré réellement avec `scripts/01_leads.sh` (siège dans le 28, catégorie PME, EI inclus).

**Gisement (total annoncé par l'API, entreprises actives, siège en Eure-et-Loir)**

| Requête | Entreprises |
|---|---|
| 43.22A + 43.21A (plombiers, électriciens) | 1 022 |
| `nafs_artisans` (7 codes) | 2 975 |
| `nafs_commerces` (4 codes) | 1 234 |

Sans `--siege`/PME, la même requête 43.22A+43.21A annonce 1 220 entreprises, dont en tête les groupes nationaux (SPIE, Eiffage Énergie, Equans…) : inutilisable pour l'offre.

**Test imposé : `leads.js --naf 43.22A,43.21A --dept 28 --max 30` puis `enrich.js --max 12`** (exécuté 5 fois au fil des réglages)

| Mesure | Résultat |
|---|---|
| Collecte 30 leads | ~2 s (4 pages de 25, 3 en parallèle) |
| Enrichissement 12 leads, `--sans-ddg` | ~10 s ; sites : 2/12 (david-elec.fr « moyenne », julienrousseau.com « moyenne ») ; e-mails MX-validés : 0 à 1 |
| Enrichissement 12 leads, DDG actif, DDG répondant | ~30 s ; 12/12 « sites » avant durcissement, dont 9–10 « basse » et des fiches d'annuaires : **0 lead exploitable** |
| Enrichissement 12 leads, DDG actif, DDG bloqué (9 pages anti-robot sur 12) | ~20 s ; sites : 2/12 ; e-mails : 0 |
| File produite par ce test seul | 0 lead (plombiers/électriciens individuels du 28 : quasi aucun site propre avec e-mail) |

**Exécution élargie : `--groupe tous --max 40 --max-enrich 60`** (80 leads collectés, 60 enrichis, 87 s au total)

| Mesure | Résultat |
|---|---|
| Collecte 2 requêtes × 40 leads | ~4 s |
| Enrichissement 60 leads (concurrence 3, DDG actif mais 49/60 pages anti-robot) | ~80 s, soit ~1,3 s/lead |
| Sites trouvés | 11/60 : 7 haute, 2 moyenne, 2 basse (devinette de domaine surtout) |
| E-mails MX-validés | 8 |
| **File `data/queue.csv`** (après filtre, avec le test imposé) | **7 leads** sur 110 lignes enrichies (≈ 6 %) : 4 e-mails génériques, 3 webmail, 0 nominatif ; motifs de rejet : 97 sans site, 3 confiance basse, 3 sans e-mail |

Exemples de la file : AUX CO 'PAINS GOURMANDS (La Bazoche-Gouet, auxcopainsgourmands.com, haute) ; RABAROT FRERES (Gommerville, rabarot-freres.fr, haute) ; CLAVEAU STYLES (Cloyes-les-Trois-Rivières, claveaustyles.fr, haute) ; GROUPE ROY ENERGIE (Toury, grouperoyenergie.com, haute).

**Après ajout de la cible TPE (5 novembre 2026, soir)** : `scripts/01_leads.sh --depuis-enrichis data/raw/enrichis_20261105-211127.csv` (80 lignes) → 20 rejets `hors_cible_taille` (dont GROUPE ROY ENERGIE : effectif 22, CA 47,3 M€, 3 établissements, mot GROUPE ; AUX CO 'PAINS GOURMANDS : effectif 12, CA 3,0 M€, 3 établissements ; LA CHARPENTE COURVILLOISE : effectif 12 ; LE TIRE BOUCHON : 3 établissements), 56 `sans_site`, 1 `sans_email`. **File : 3 leads**, tous webmail : RABAROT FRERES (Gommerville, rabarot-freres.fr, effectif 02) ; CLAVEAU STYLES (Cloyes-les-Trois-Rivières, claveaustyles.fr, effectif 03) ; CHAPE LIQUIDE LEDOUX 28 (Ver-lès-Chartres, chape-liquide-ledoux-28.fr, effectif 02). Le rendement passe à ≈ 4 % : la cible TPE renforce le besoin de collecter large.

**Secours DuckDuckGo derrière le proxy** : fonctionne par intermittence. Premières sondes : page anti-robot (HTTP 202, « anomaly ») ; puis ~35 requêtes servies normalement (27 sites sur 30 leads, mais surtout des fiches d'annuaires, d'où le durcissement de la vérification) ; puis blocage de la plupart des requêtes (9/12, 49/60). Il est laissé actif par défaut (`utiliser_ddg: true`) parce que son échec est détecté et sans effet sur la file ; pour une exécution rapide et reproductible, `--sans-ddg`.

**Ordre de grandeur pour une file quotidienne** : à ~6 % de rendement, obtenir ~10 leads exploitables demande d'enrichir ~150–200 leads (3–5 min), soit `max_par_requete` 100 et `max_enrichissement` 200, ou l'ajout de départements voisins.

## 7. Limites connues

- **Cible TPE** : `nb_etablissements` est le nombre d'établissements *ouverts* (API) ; un commerçant avec deux boutiques et un dépôt est écarté par `nb_etablissements_max: 2` (ajuster dans `config.json` si la cible s'élargit). Le CA n'est connu que pour les sociétés qui publient leurs comptes ; absent, il ne compte pas. L'effectif INSEE date de l'avant-dernière année.
- **La majorité des artisans ruraux n'ont pas de site propre** : ils ont une fiche Google ou une page Facebook (non collectées, hors périmètre). Le rendement « site propre vérifié + e-mail » est donc faible ; il faut collecter large (`max_par_requete` 100–200 par groupe) pour alimenter une file d'une dizaine de leads/jour. Les leads « sans site » restent dans `data/queue_rejets.csv` (motif `sans_site`) : c'est la cible naturelle de l'offre « création » de la même page.
- **DuckDuckGo** : fonctionne derrière le proxy mais renvoie par intermittence une page anti-robot (HTTP 202, « anomaly ») ; `enrich.js` la détecte, compte les occurrences et laisse le lead « sans site ». Relancer plus tard avec `--depuis-bruts` sur les leads non trouvés. Le secours « basse » (premier résultat non vérifié) n'alimente jamais la file.
- **Pas de téléphone ni d'e-mail dans SIRENE** : les contacts viennent uniquement des sites ; les téléphones extraits par regex peuvent contenir du bruit (numéros de la page, pas forcément de l'entreprise) — ne pas les utiliser sans vérification.
- **Homonymes** : un site « moyenne » n'a pas été relié à la ville ; l'audit (composant B) doit confirmer que le site parle bien de l'entreprise avant tout e-mail.
- **API** : réinitialisations de connexion ponctuelles via le proxy (retry ×7 intégré) ; plafond 10 000 résultats par requête (sans objet au niveau département × NAF, ~1 000 ici).
- **MX natif indisponible** dans l'environnement d'exécution (ENODATA) : secours DoH ; si les deux échouent, l'e-mail est écarté (strict).
- **NAF 2025** : `leads.js` filtre sur NAF rév. 2 ; la colonne `naf_2025` existe dans `data/raw/*` mais n'est pas utilisée.
- **Dirigeants** : chaîne RNE brute (« PRENOM1 PRENOM2 NOM (NOM USAGE) (qualité) ») : à nettoyer pour la personnalisation (composant e-mail).
- `01_leads.sh` ne relance pas les leads déjà présents dans `data/raw/*` : chaque exécution interroge à nouveau l'API (ordre stable côté API ⇒ mêmes 100 premiers). Pour avancer dans la liste : augmenter `max_par_requete` ou découper par `--depts`/`--nafs` ; le `ledger.csv` évite les doublons en aval.
