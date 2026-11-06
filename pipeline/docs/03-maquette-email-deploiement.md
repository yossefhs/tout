# 03 — Maquette, e-mail, registre, déploiement (composant C)

Quatre briques de la chaîne de prospection Clients Ici, dans `/home/user/refonte-vitrine/pipeline`. Rédigé le 2026-11-05. Aucun e-mail n'est envoyé, rien n'est publié, aucun site tiers n'est consulté par ces scripts : ils transforment des fichiers locaux (spec, audit, lead) en fichiers locaux (maquette, e-mail, registre, dossier d'aperçu prêt à committer).

Interpréteur : `/home/user/.venv-webtest/bin/python` (shebang des scripts). Pour les tests navigateur : `export PLAYWRIGHT_BROWSERS_PATH=/home/user/.venv-webtest/ms-playwright` (le script de test le force lui-même).

## 1. Maquette de page d'accueil

### Fichiers

- Gabarit : `templates/maquette.html` (marqueurs `{{var}}`, `{{#if clé}}…{{/if}}`, `{{#each liste}}…{{/each}}`, `{{.}}` ; toutes les valeurs sont échappées en HTML).
- Générateur : `scripts/build_maquette.py`.
- Vérificateur : `scripts/test_maquette.py` (Playwright + Lighthouse en option).
- Exemples de spec (fictifs, à ne pas confondre avec un prospect) : `templates/exemples/spec-exemple-plomberie.json` (bâtiment, devis), `spec-exemple-boulangerie.json` (commerce, contact), `spec-exemple-coiffure.json` (service, appel).
- Sorties de test conservées : `out/maquette-test/<palette>/index.html`, `out/maquette-test/captures/*.png` (375, 768, 1440 px), `out/maquette-test/lighthouse-*.json`.

### Usage

```bash
cd /home/user/refonte-vitrine/pipeline
scripts/build_maquette.py --spec spec.json --out out/<lead>/maquette/index.html [--audit out/<lead>/audit.json] [--agence "Clients Ici"]
scripts/test_maquette.py out/<lead>/maquette --out out/<lead>/maquette/captures [--lighthouse]
```

`build_maquette.py` écrit `index.html` (écriture atomique) et imprime une ligne JSON (`ok`, `out`, `octets`, `palette`, `objectif`, `titre`, `sections`, `constats_audit_affiches`). Code 2 si le spec est invalide (nom absent, palette ou objectif inconnus) ou si la sortie enfreint un garde-fou (lien `tel:`/`mailto:`, ressource externe, `noindex` absent, bandeau absent) : rien n'est écrit dans ce cas.

### Le spec : uniquement des informations confirmées

| Clé | Type | Rôle |
|---|---|---|
| `nom` (obligatoire) | texte | marque dans l'en-tête, surtitre, pied de page |
| `metier` | texte (libellé NAF ou texte du site) | H1 (avec la ville) et pied de page ; `metier_court` facultatif remplace `metier` dans le H1 si le libellé NAF est long |
| `ville` | texte | H1 « <métier> à <ville> », surtitre. Sans `ville`, le H1 et le `<title>` sont le métier seul (ou le nom) : aucun lieu n'est affirmé, même si `zone` est renseignée ; avec `ville` mais sans `zone`, « <métier> à <ville> » reste acceptable (la ville vient du siège SIRENE) |
| `zone` | texte, seulement si le site l'énonce | section « Zone d'intervention » |
| `tel`, `email`, `adresse` | texte | hero et section contact ; `tel` et `email` affichés en texte, non cliquables |
| `services` | liste de chaînes ou `{titre, detail}` (12 max) | section « Prestations » (grille 3 colonnes à partir de 6 entrées) |
| `horaires` | liste de chaînes `"Jours : heures"` ou `{jours, heures}` | section « Horaires » |
| `slogan` | texte du site | accroche sous le H1 (en italique pour la palette commerce) ; sinon l'accroche est « <nom>, <métier>, à <ville>. » |
| `preuves_verifiees` | liste (ex. « SIRET affiché sur le site ») | section « Garanties et mentions », avec la note « reprises telles qu'affichées sur le site actuel » |
| `palette` | `batiment` \| `commerce` \| `service` | direction graphique |
| `objectif` | `devis` \| `appel` \| `contact` | libellé du bouton principal, titre et champs du formulaire |
| `domaine_source` | texte | domaine cité dans la mention de pied de page (sinon pris dans l'audit) |

Toute section sans donnée est omise (menu compris). Aucune statistique, note, avis, photo ou réalisation n'est générée : il n'y a pas de champ pour cela dans le gabarit. Garde-fou `verifier_titre` : le H1 et le `<title>` (« <H1> | <nom> (maquette) ») ne peuvent être que `metier_court`/`metier`, « <métier> à <ville> » (ville présente dans le spec) ou `nom` ; toute autre valeur fait échouer la génération (code 2).

`--audit audit.json` sert à deux choses : lister les constats de gravité haute et moyenne (6 au plus) dans un volet repliable « Points relevés sur le site actuel » du bandeau, et nommer le domaine dans le pied de page. Un audit absent ou illisible est signalé dans `avertissements` et n'empêche pas la génération.

### Direction graphique (une par palette, mobile d'abord)

| Palette | Couleurs | Typographie | Le geste |
|---|---|---|---|
| `batiment` | fond `#f6f3ec`, bleu profond `#163a5c`, ocre `#d08a2a`, encre `#17202b` | Inter / Helvetica, titres gras serrés (800, −0,025 em), bouton ocre | ruban hachuré ocre et bleu (ruban de chantier) sous le hero et au-dessus du pied de page |
| `commerce` | crème `#f7f1e4`, vert foncé `#1e4d3b`, accent `#c89f5c`, encre `#1d2a24` | Georgia / serif partout, titres en graisse normale, slogan en italique, interligne 1,68 | store banne (rayures verticales vert/or et festons) sous le hero |
| `service` | sable `#f3ece2`, prune `#4b2a4f`, accent `#c99a63`, encre `#2a1f2e` | Trebuchet / Segoe, graisse 600, rayons 14–22 px | grand disque sable derrière le titre, prestations en pastilles claires |

Structure commune : bandeau sombre « Proposition non officielle — aperçu pour discussion. Maquette préparée par Clients Ici ; ce n'est pas le site de <nom>. », en-tête (nom + navigation des sections présentes), hero (surtitre nom + ville, H1 métier à ville, accroche, bouton vers `#contact`, numéro en texte), Prestations, Zone, Garanties et mentions, Horaires, Contact (coordonnées + formulaire de démonstration), pied de page avec « Maquette réalisée par Clients Ici à partir des informations publiques de <nom> (site <domaine>) ; aucune donnée collectée. », barre fixe en bas d'écran sur mobile (≤ 760 px) avec le bouton principal.

Qualité intégrée : HTML sémantique (`header`, `nav`, `main`, `section` avec `aria-labelledby`, `footer`, `address`, `dl`), lien d'évitement, focus visible (`outline` 3 px), contrastes AA (Lighthouse accessibilité 100 sur les trois palettes), `prefers-reduced-motion` (pas d'animation de toute façon), `<meta name="robots" content="noindex, nofollow">`, `referrer no-referrer`, favicon `data:` (aucune requête), aucune police ni image ni script externe, aucun tracker.

Formulaire : `novalidate`, validation locale (nom ≥ 2 caractères, téléphone ≥ 10 chiffres, e-mail avec `@` et point, message ≥ 3 caractères), messages d'erreur sous les champs, `aria-invalid`, focus sur le premier champ fautif ; à la soumission valide, `role="status"` affiche « Démonstration : ce formulaire n'envoie rien. » et rien d'autre ne se passe (ni requête, ni navigation, ni faux succès). Note visible au-dessus : « Formulaire de démonstration : aucune information n'est envoyée ni enregistrée. »

Liens `tel:`/`mailto:` du prospect : neutralisés (span avec `title` « Numéro affiché à titre d'aperçu : volontairement non cliquable dans cette maquette, pour ne provoquer aucun appel réel. ») et phrase explicative dans la section contact. Le générateur et `publish_maquette.py` refusent toute sortie qui en contiendrait.

### Tests exécutés (2026-11-05)

`scripts/test_maquette.py` sert les maquettes par HTTP local (port libre), puis pour chaque maquette : 375×812, 768×1024, 1440×900 (débordement `scrollWidth` vs `innerWidth`, éléments hors cadre, erreurs console et exceptions JS, captures pleine page ; **toute requête vers autre chose que le serveur local est bloquée avant d'être émise, listée dans `requetes_externes` et comptée KO**) ; à 375 px : soumission vide (erreurs attendues), saisie valide (statut attendu, aucune requête réseau : la seule requête observée est le document lui-même), parcours clavier Tab (lien d'évitement en premier, chaque élément `:focus-visible` a un contour), garde-fous (pas de `tel:`/`mailto:`, `noindex`, bandeau, mention de pied de page, un seul H1, plus petit texte ≥ 12 px). `--lighthouse` ajoute Lighthouse 12 mobile.

| Maquette | Résultat | Lighthouse (perf / accessibilité / bonnes pratiques / SEO) |
|---|---|---|
| Exemple Plomberie (bâtiment, devis, avec audit factice) | 0 KO ; 1 requête réseau ; 14 arrêts clavier ; texte min 13,76 px | 100 / 100 / 100 / 60 |
| Exemple Boulangerie (commerce, contact) | 0 KO ; 1 requête ; 11 arrêts ; 14,4 px | 100 / 100 / 100 / 60 |
| Exemple Coiffure (service, appel) | 0 KO ; 1 requête ; 10 arrêts ; 14,4 px | 100 / 100 / 100 / 60 |

Le 60 en SEO vient uniquement de l'audit `is-crawlable` : la page est `noindex`, c'est voulu. Le script tolère cet audit et compte KO tout autre audit sous 0,9. Deux corrections ont été faites pendant les tests : le disque de la palette service chevauchait le H1 (décalé), et le script de test prenait le `PLAYWRIGHT_BROWSERS_PATH` de l'environnement (navigateur 1248 absent) : il force désormais le chemin du venv. Sur les captures pleine page, la barre fixe mobile apparaît au milieu de l'image : artefact de capture, pas de la page.

Erreurs vérifiées : spec sans `nom`, palette inconnue, fichier absent → JSON `ok:false`, code 2, rien d'écrit.

Tests automatisés : `scripts/test_pipeline.py` (unittest, ~15 s) vérifie entre autres que `test_maquette.py` renvoie le code 1 pour une maquette qui charge une image externe (KO « requête(s) externe(s) bloquée(s) ») et pour une maquette sans bandeau (KO « bandeau de démonstration absent »), et que le H1/`<title>` d'un spec sans ville ni zone ne contient pas de lieu. Relancé le 2026-11-05 au soir sur les trois exemples : 0 KO, 1 requête réseau (le document), `requetes_externes` vide.

## 2. E-mail de prospection

### Fichiers

- Script : `scripts/build_email.py` ; banque de phrases : `templates/email_phrases.json`.
- Fixtures de test : `templates/exemples/audit-factice.json` (audit minimal factice au schéma d'`audit_site.py` : `analyse.constats [{id,type,gravite,titre,preuve,consequence_possible,correction}]`, `analyse.verdict`, `pages`, `cible`) et `templates/exemples/lead-exemple.json` (mêmes clés qu'une ligne de `data/queue.csv`).
- Sorties de test : `out/email-test/email-sans-maquette.{json,txt}`, `email-avec-maquette.{json,txt}`, `email-audit-example-com.txt` (sur l'audit réel d'example.com, test 2 du composant B).
- `config.json` : clé `expediteur` ajoutée (nom, entreprise, email, tel, adresse, url_offre, url_confidentialite) ; les autres clés n'ont pas été touchées. Si la clé manque, le script utilise les mêmes valeurs par défaut.

### Usage

```bash
scripts/build_email.py --audit out/<lead>/audit.json --lead out/<lead>/lead.json --config config.json \
  [--maquette-url https://clientsici.fr/apercu/<jeton>/] --out out/<lead>/email.json [--graine N]
```

Sortie `email.json` : `objets` (2), `corps`, `signature`, `bloc_information`, `texte_complet`, `nb_mots_corps`, `nb_mots_total`, `constats_utilises` (id, catégorie, gravité, titre), `constats_disponibles`, `verdict_audit`, `maquette_url`, `whatsapp` et `sms` (`texte`, `statut: "brouillon — conditions de contact à vérifier"`, `nb_caracteres`), `controles` (`ok`, `problemes`), `avertissements`. Un `email.txt` prêt à coller est écrit à côté. Codes : 0 écrit et contrôles passés ; 1 écrit mais un contrôle échoue (`problemes`) ; 2 fichier ou argument invalide (`--maquette-url` doit être une URL `https` complète) ; 3 aucun constat exploitable ou verdict « informations insuffisantes » (pas d'e-mail à écrire).

### Règles appliquées (skill cold-email)

- Constats : triés par gravité (haute, moyenne, basse) puis par id ; les constats « information » (générateur grand public) et « page d'accueil non chargée » sont exclus ; une seule catégorie par e-mail ; 2 constats si une combinaison tient dans la plage, sinon 1.
- Catégorisation par expressions régulières sur le titre du constat (clé `motifs` de la banque) : https absent, http→https non forcé, viewport, débordement, performance faible/moyenne, noindex, robots, title, description, téléphone non cliquable, bouton d'appel hors écran, ville absente, canonical, lien en erreur, poids, H1, alt, LocalBusiness, copyright, lang, texte petit, erreurs JS, devis, www, score Lighthouse. Un titre non reconnu est ignoré (ajouter un motif dans la banque).
- Corps : salutation, ouverture (« j'ai testé l'affichage de <domaine> sur téléphone… » : un test automatisé, jamais une visite humaine, donc pas de « je suis passé sur… » ni « depuis mon téléphone »), 1 à 2 constats formulés simplement et sans dénigrer, bénéfice concret, maquette (phrase « avec URL » seulement si `--maquette-url`, sinon proposition de la préparer sans pression), une seule question. **80 à 110 mots** au compteur interne ; le script essaie toutes les combinaisons de variantes et retient la première dans la plage, dans un ordre mélangé par une graine dérivée du domaine (`sha256`) : deux leads reçoivent des textes différents, un même lead reçoit toujours le même texte (`--graine` pour forcer).
- **Méthode de comptage** (`compter_mots`, expression `[^\W_]+(?:['’\-][^\W_]+)*`) : un mot est une suite de lettres ou de chiffres ; une apostrophe ou un trait d'union *entre* deux morceaux ne coupe pas (« l'adresse » = 1 mot, « Nogent-le-Rotrou » = 1) ; ponctuation, guillemets et tirets isolés ne comptent pas ; une URL compte un mot par segment (« https://clientsici.fr/apercu/abc/ » = 5). Ce compte est celui de `nb_mots_corps` ; il est en général inférieur de quelques unités à un `split()` sur les espaces (qui compterait les guillemets) et supérieur pour les URL.
- **Chiffres et mesures** : aucun chiffre dans le corps, donc jamais de score Lighthouse, de « /100 », de secondes ni de pourcentage : une mesure Lighthouse unique n'est pas reproductible et un chiffre ne serait employé qu'avec deux mesures concordantes, ce que la chaîne ne fait pas. La lenteur est un constat sans chiffre (« s'affiche lentement », « met longtemps à s'afficher »). Le contrôle `MOTIFS_MESURE` refuse « Lighthouse », « score », « /100 », « n s/ms » et « n % » ; `MOTIFS_VISITE` refuse toute prétention de visite humaine dans le corps, le WhatsApp et le SMS.
- Objets : 2, ≤ 50 caractères, sans majuscules criardes, sans « urgent », **sans « site vitrine »** (on ne sait pas si le site en est un : « <domaine> sur téléphone », « affichage de <domaine> sur mobile »…), tirés des objets de la catégorie puis des génériques (« votre site <domaine> », « un point sur votre site »).
- Signature : Guillaume Samama, Clients Ici, `https://clientsici.fr/refonte-site-vitrine/`, e-mail, adresse postale. Bloc information après `--` : origine des coordonnées (« votre site <domaine> »), « répondez STOP pour ne plus recevoir de message », lien `/confidentialite/`.
- Contrôles automatiques : longueur des objets, « urgent », « site vitrine » dans un objet, 80–110 mots, aucune balise HTML, aucun tiret cadratin, aucun lien autre que la maquette, aucun chiffre ni mesure d'outil dans le corps (hors URL et domaine), aucune prétention de visite humaine (corps, WhatsApp, SMS), exactement une question, aucun lien raccourci. Pas de pixel, texte brut.
- WhatsApp (2–3 phrases) et SMS (< 160 caractères visés, 229 obtenus sur l'exemple : à raccourcir à la main si besoin) : marqués brouillon ; les conditions de contact (consentement, numéro professionnel) restent à vérifier avant tout usage.

### Tests exécutés

| Test | Résultat |
|---|---|
| audit factice, sans maquette (2026-11-05 soir, règles ≤ 110 mots) | exit 0 ; 109 mots ; objets « « non sécurisé » sur exemple-plomberie.example », « exemple-plomberie.example sur téléphone » ; constats C01 (https non forcé) + C02 (performance moyenne, formulée « s'affiche un peu lentement », sans chiffre) ; contrôles OK ; `out/email-test/email-sans-maquette.{json,txt}` |
| audit factice, `--maquette-url` (2026-11-05 soir) | exit 0 ; 104 mots ; l'URL de la maquette figure dans le corps ; 1 question ; `out/email-test/email-avec-maquette.{json,txt}` |
| 8 graines, avec et sans maquette (`test_pipeline.py`) | 16 corps entre 100 et 110 mots, objets sans « site vitrine », aucun chiffre, aucune prétention de visite, contrôles OK |
| audit réel gre-enr.fr (Lighthouse performance mesurée) | exit 0 ; 110 mots ; constats C03 (performance faible) + C02 (page lourde) rendus sans aucun chiffre ; sortie hors `out/` (lead désormais hors cible TPE) |
| audit réel example.com (composant B) | exit 0 ; 100 mots ; C01 + C02 (description absente) |
| audit réel clientsici.fr (4 constats, 2 exploitables) | exit 0 ; 101 mots ; C01 + C03 |
| 6 graines sur le même audit (version 80–120 mots, historique) | 6 corps distincts (112 à 120 mots), objets variés, contrôles OK |
| audit absent ; verdict « informations insuffisantes » ; `--maquette-url ftp://x` | exit 2 ; exit 3 ; exit 2 |

## 3. Registre et liste d'opposition

Script : `scripts/ledger.py`. Fichiers : `data/ledger.csv` (`date;siren;domaine;email;statut;thread_id;draft_id;maquette_url;notes`) et `data/opposition.csv` (`valeur;type;date;source`), séparateur `;`, UTF-8, lus avec tolérance au BOM. Créés avec leur seul en-tête **uniquement s'ils n'existent pas** (`O_CREAT|O_EXCL`, ou en-tête posé sur un fichier vide) ; toute réécriture passe par un fichier temporaire puis `os.replace` ; un verrou `flock` sur `data/.ledger.lock` sérialise les écritures (ce fichier vide est créé par le script). Statuts : queued, audited, skipped, drafted, sent, replied, interested, stop, bounced, won, lost.

```bash
scripts/ledger.py add   --siren 000000000 --domaine exemple.fr --email contact@exemple.fr --statut queued [--notes ...] [--force]
scripts/ledger.py set   --domaine exemple.fr [--statut drafted] [--thread_id T] [--draft_id D] [--maquette_url U] [--notes N] [--ajouter-note]
scripts/ledger.py check --email contact@exemple.fr    # ou --domaine exemple.fr
scripts/ledger.py stop  --valeur contact@exemple.fr --source "réponse STOP du 2026-11-05" [--type email|domaine|siren]
scripts/ledger.py list  [--statut sent]
# --data-dir <dossier> pour un autre emplacement
```

Comportements : `add` normalise (domaine sans schéma ni `www.`, e-mail en minuscules, SIREN chiffres), refuse un doublon (domaine ou e-mail déjà présent ; `--force` pour une seconde ligne) et refuse toute valeur présente en opposition ; `set` modifie toutes les lignes du domaine/e-mail ; `check` renvoie `contact_autorise` (faux si opposition, ou statut drafted/sent/replied/interested/stop/bounced/won/lost) et `motif_blocage` ; `stop` ajoute la valeur en opposition (type détecté : `@` → email, 9 chiffres → siren, sinon domaine) et passe en `stop` les lignes du registre correspondantes (une adresse sur le domaine propre de l'entreprise bloque tout le domaine, pas pour les webmails). Sortie JSON sur stdout.

Tests (sur un dossier de test, puis une lecture seule du registre réel) : add, doublon refusé (exit 1), statut invalide (exit 2), set, set introuvable (exit 1), check avant/après, stop par e-mail puis domaine puis SIREN, add refusé par opposition, 20 `add` en parallèle (20 lignes, aucune perte ni corruption), fichier avec BOM lu correctement, `check --domaine julienrousseau.com` sur `data/ledger.csv` réel (non trouvé, autorisé). Le registre réel n'a pas été modifié (toujours l'en-tête seul).

## 4. Déploiement (NON TESTÉ : aucun dépôt ni accès FTP dans cette session)

- `deploy/.github-workflows-deploy.yml` : à copier dans le dépôt du site sous `.github/workflows/deploy.yml`. À chaque push sur `main` touchant `site/**` (ou à la main via `workflow_dispatch` avec case `dry_run`), un contrôle vérifie que chaque `site/apercu/<jeton>/` contient un `.htaccess` avec `noindex`, puis `SamKirkland/FTP-Deploy-Action@v4.3.5` envoie `site/` vers `./www/` en FTPS (port 21) avec les secrets `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD` ; exclusions `.git*`, `node_modules`, `*.map`, `.DS_Store`, `*.tmp`, `README*.md`, `captures/**` ; état de synchronisation `.ftp-deploy-sync-state.json` ; `dangerous-clean-slate: false`. Syntaxe YAML validée avec `js-yaml` (jobs, déclencheurs, trois étapes). À adapter : `server-dir` (racine web OVH), `protocol: sftp` et `port: 22` si l'hébergement l'offre.
- `deploy/apercu.htaccess` : `X-Robots-Tag "noindex, nofollow, noarchive, nosnippet"`, `Referrer-Policy no-referrer`, `nosniff`, `Cache-Control private, no-store`, `Options -Indexes`, `DirectoryIndex index.html`, bloc Basic Auth commenté (`.htpasswd` hors racine web). Non testé sous Apache.
- `scripts/publish_maquette.py --maquette <index.html> [--site-dir /home/user/refonte-vitrine/site] [--base-url https://clientsici.fr] [--jeton …]` : vérifie la maquette (mêmes garde-fous que le générateur), tire un jeton de 20 caractères `[a-z0-9]` (`secrets`), copie `index.html` et `.htaccess` dans `<site-dir>/apercu/<jeton>/`, pose un `.htaccess` (`-Indexes`, noindex) à la racine d'`apercu/` et renvoie `{jeton, chemin, url: https://clientsici.fr/apercu/<jeton>/, publie: false}`. `--supprimer <jeton>` retire le dossier. Rien n'est envoyé : la publication passe par `git add site/apercu && git commit && git push`. Testé sur un dossier de test : copie identique (`cmp`), jeton imposé, maquette introuvable (exit 2), jeton invalide (exit 2), maquette contenant un lien `tel:` refusée (exit 1), suppression puis suppression d'un jeton absent (exit 1). Le dossier `site/` par défaut n'existe pas encore dans `/home/user/refonte-vitrine/` : il est créé à la première publication préparée, ou passer `--site-dir`.

## 5. Chaîne complète testée (dossier de test)

`build_maquette.py` (spec + audit factice) → `test_maquette.py` (0 KO) → `publish_maquette.py` (URL `https://clientsici.fr/apercu/cae2ykvz8bctq1105oqw/`) → `build_email.py --maquette-url` (120 mots à l'époque, plage 80–120 ; aujourd'hui 80–110) → `ledger.py add … audited` puis `set … --statut drafted --maquette_url …` puis `check` (bloqué : statut drafted). Toutes les étapes en moins de 20 s hors Lighthouse.

## 6. Limites et points ouverts

- Le spec de maquette doit être rempli en amont (composant D / orchestrateur) à partir de `analyse.a_preserver` de l'audit et d'une relecture humaine : le générateur ne vérifie pas que les informations viennent du site, il refuse seulement d'inventer (pas de champ pour avis, chiffres, photos).
- Les polices sont des familles système (Inter, Georgia, Trebuchet) : rendu légèrement différent selon la machine du prospect ; aucune police web n'est chargée pour garder zéro requête externe.
- La maquette est une page unique sans images : pour un prospect dont le site vit par ses photos, prévoir une variante avec ses propres photos (hors périmètre, elles seraient des ressources locales à copier).
- E-mail : le runbook `prospection-run` cite encore l'avertissement « aucune combinaison entre 80 et 120 mots » ; le texte émis est désormais « … entre 80 et 110 mots » (même forme, seules les bornes changent). La catégorisation repose sur les titres d'`audit_site.py` ; un nouveau type de constat doit être ajouté à `email_phrases.json`. Le SMS dépasse 160 caractères sur l'exemple. WhatsApp et SMS restent des brouillons tant que les conditions de contact (consentement, numéro pro) ne sont pas vérifiées.
- Registre : `check` bloque dès le statut `drafted`, pour éviter deux brouillons sur un même prospect ; un statut `queued` ou `audited` reste autorisé. Les composants Leads (`filter_queue.py`) lisent les mêmes fichiers avec les mêmes en-têtes.
- Déploiement : rien n'a pu être exécuté (ni dépôt Git, ni secrets, ni accès OVH). Première mise en service : lancer le workflow en `dry_run` avant un vrai envoi, vérifier `server-dir`, et contrôler qu'une URL d'aperçu renvoie bien l'en-tête `X-Robots-Tag`.
- Lighthouse n'a été exécuté que sur des pages locales (sans latence réseau réelle).

## Addendum 2026-11-05 — envoi et déploiement depuis le Mac (Remote Control)

Guillaume indique que les fichiers d'accès à la messagerie et à l'hébergement OVH sont sur son Mac. Deux usages, sans que les mots de passe transitent par la conversation :

1. **Déploiement du site** : une session rattachée au dossier du Mac (Claude Desktop → Réglages → Claude Code → Remote Control → ajouter le dossier) peut exécuter l'envoi FTP/SFTP de `site/` vers la racine web OVH en lisant les identifiants dans le fichier local (`lftp` ou `curl --netrc-file`), sans les afficher. Même chose pour chaque nouvel aperçu `site/apercu/<jeton>/`.
2. **Envoi SMTP depuis guillaume@clientsici.fr** : `scripts/send_email.py --provider smtp` lit `SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD` ou `SMTP_CREDENTIALS_FILE` (JSON `{"host","port","user","password"}`, ex. OVH `ssl0.ovh.net`, port 465). Les sessions planifiées dans le cloud ne peuvent pas lire de secret local : pour elles, rester sur `brevo` (clé injectée par le proxy) ou faire tourner la chaîne sur le Mac via une tâche planifiée Cowork liée à cet ordinateur.
