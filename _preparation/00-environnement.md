# 00 — Environnement, skills et limites

Date : 2026-11-05. Environnement : session Claude Code cloud (conteneur Linux éphémère), répertoire de travail `/home/user` (pas de dépôt git). Node 22, Python 3.13.18, Chromium Playwright pré-installé (`/opt/pw-browsers/chromium-1243`).

> Statut au moment de la rédaction : **URL du prospect non fournie**. Ce fichier documente la préparation ; il sera copié et complété dans le dossier du prospect dès que l'URL sera connue.

## Sources consultées (dépôts clonés en profondeur 1, lecture des README, SKILL.md et scripts d'installation avant toute exécution)

| Dépôt | Commit cloné | Date du commit | Contenu utile |
|---|---|---|---|
| https://github.com/AgriciDaniel/claude-seo | `6be93f4` (plugin v2.5.0) | 2026-10-22 | skill hub `seo` + 25 sous-skills `seo-*`, 19 agents, scripts Python, runtime isolé |
| https://github.com/anthropics/skills (sparse) | `ca45fc4` | 2026-10-28 | `skills/frontend-design`, `skills/webapp-testing` |
| https://github.com/coreyhaines31/marketingskills | `88c79f6` | 2026-10-30 | `skills/copywriting` 2.3.2, `skills/cold-email` 2.2.1, `skills/prospecting` 1.5.0 |
| https://code.claude.com/docs/en/skills | page consultée le 2026-11-05 | — | emplacement projet `.claude/skills/<nom>/SKILL.md` ; les skills projet se chargent « dans les sessions de ce dépôt » |

Noms réellement exposés (frontmatter `name:`) : `seo`, `seo-page`, `seo-technical`, `seo-schema`, `seo-local`, `seo-images`, `seo-content`, … (26 au total côté claude-seo) ; `frontend-design` ; `webapp-testing` ; `copywriting` ; `cold-email` ; `prospecting`. Le nom de dépôt `claude-seo` n'est pas un nom de skill : le skill principal s'appelle `seo`.

## Méthode d'installation retenue

- Portée **projet** : `/home/user/.claude/skills/` et `/home/user/.claude/agents/` (créés vides, rien d'existant écrasé). Aucune écriture dans la portée utilisateur `~/.claude`, aucun `settings.json` modifié, aucun hook enregistré.
- claude-seo : reproduction du `install.sh` officiel (lu intégralement) en remplaçant `$HOME/.claude` par la portée projet, puis réécriture du jeton `${CLAUDE_PLUGIN_ROOT}` vers les chemins projet comme le fait le script ; runtime Python isolé créé par `scripts/claude-seo setup` (venv dans le dossier du skill, Chromium Playwright dédié). Extensions (DataForSEO, Banana, Firecrawl, Matomo) non installées : non demandées. Le hook `PostToolUse` fourni n'est pas enregistré (il exigerait une modification de mes réglages).
- anthropics/skills : copie des deux dossiers de skills (méthode documentée) ; venv de test `/home/user/.venv-webtest` avec Playwright Python pour `webapp-testing`.
- marketingskills : « Option 4 : clone and copy » du README (le CLI `npx skills` est interactif et non nécessaire ; le `/plugin` n'existe pas en session cloud, comme le précise le README).

## Skills déjà présents avant installation (synchronisés depuis le compte claude.ai)

`anthropic-skills:copywriting` (version différente et plus ancienne, sans numéro de version), `anthropic-skills:seo-audit` (marketingskills, pas claude-seo), `anthropic-skills:impeccable`, `anthropic-skills:agent-browser`, etc. Ils restent intacts. Collision de nom possible pour `copywriting` : la copie projet est la version coreyhaines31 2.3.2.

## Statut par skill (vérifié le 2026-11-05, commandes réellement exécutées)

| Skill (nom exposé) | Source / version | Emplacement | Statut | Preuve |
|---|---|---|---|---|
| `seo` (+ 25 sous-skills `seo-*`, 19 agents `seo-*`) | AgriciDaniel/claude-seo v2.5.0, commit `6be93f4` | `/home/user/.claude/skills/seo/` …, `/home/user/.claude/agents/` | **installé, chargé** (apparaît dans la liste des skills et des agents de la session) | `scripts/claude-seo doctor --json` → `ready: true, browser_ready: true, mode: manual` ; `claude-seo run metadata_template.py --help` → exit 0 ; 45 fichiers avec le lanceur réécrit vers le chemin projet |
| `frontend-design` | anthropics/skills commit `ca45fc4` | `/home/user/.claude/skills/frontend-design/` | **installé, chargé** | `diff -rq` avec le clone : identique ; listé dans la session |
| `webapp-testing` | anthropics/skills commit `ca45fc4` | `/home/user/.claude/skills/webapp-testing/` | **installé, chargé, utilisé** (chargé via l'outil Skill pour test) | `with_server.py --help` → OK ; Playwright Python 1.64.1 dans `/home/user/.venv-webtest`, Chromium 156.0.8078.4 (`PLAYWRIGHT_BROWSERS_PATH=/home/user/.venv-webtest/ms-playwright`), capture test 375 px produite |
| `copywriting` | coreyhaines31/marketingskills 2.3.2, commit `88c79f6` | `/home/user/.claude/skills/copywriting/` | **installé, chargé** | identique au clone ; listé dans la session (distinct de `anthropic-skills:copywriting` synchronisé) |
| `cold-email` | marketingskills 2.2.1, commit `88c79f6` | `/home/user/.claude/skills/cold-email/` | **installé, chargé** | identique au clone ; listé dans la session |
| `prospecting` | marketingskills 1.5.0, commit `88c79f6` | `/home/user/.claude/skills/prospecting/` | **installé, chargé** | identique au clone ; listé dans la session |

« Utilisé » sera mis à jour dans le dossier du prospect au fil des étapes (audit, textes, design, tests, prospection).

### Résidus et points d'attention

- 11 occurrences de `${CLAUDE_PLUGIN_ROOT}` subsistent, toutes légitimes : `seo/hooks/hooks.json` et `validate-schema.py` (hook non enregistré, jamais exécuté) et une phrase explicative dans `seo/SKILL.md`.
- Le hook `PostToolUse` de claude-seo n'est pas activé : il aurait fallu modifier `settings.json`. Conséquence : pas de validation automatique des JSON-LD à l'écriture ; je valide manuellement.
- Portée utilisateur intacte : `/root/.claude/skills` contient toujours uniquement `session-start-hook` et `synced` ; aucun `/root/.claude/agents` créé ; aucun `settings.json` touché.
- Chargement : les skills projet ont été découverts par la session sans redémarrage (ils figurent dans la liste des skills disponibles après l'installation).
- L'orchestration d'installation (workflow à trois agents) a été interrompue au changement de tour avant d'enregistrer ses rapports ; les fichiers étaient en place et j'ai refait l'ensemble des vérifications ci-dessus moi-même.
- Dépendances Python de claude-seo installées dans le venv isolé `/home/user/.claude/skills/seo/.venv` (requirements.txt du dépôt) ; Chromium dédié `chromium-1248` dans `seo/ms-playwright`.
- Environnement éphémère : ces installations disparaissent à la fin du conteneur. Pour les retrouver dans une autre session, relancer cette procédure (clonage pinné + copie) ou, en session interactive locale, `/plugin marketplace add AgriciDaniel/claude-seo` et `npx skills add coreyhaines31/marketingskills --skill copywriting cold-email prospecting -a claude-code`.

### Hors périmètre, non exécuté

Extensions claude-seo (DataForSEO, Firecrawl, Matomo, Banana), agents `seo-google`/`seo-maps` nécessitant des identifiants, toute section de `cold-email`/`prospecting` relative à l'envoi, aux séquences, au scraping ou à LinkedIn.

## Données déduites du site du prestataire (clientsici.fr, consulté le 2026-11-05 — à confirmer par vous)

| Variable | Valeur lue sur clientsici.fr | Source |
|---|---|---|
| `{{NOM_PRESTATAIRE}}` | Guillaume Samama | pied de page « Éditeur du site et contact » |
| `{{AGENCE}}` | Clients Ici (EI, SIRET 889 546 347 00010, Landelles 28190) | pied de page |
| `{{EMAIL_PRESTATAIRE}}` | contact@clientsici.fr | pied de page |
| `{{TELEPHONE_PRESTATAIRE}}` | 07 56 97 45 75 (« contact de préférence par écrit ») | pied de page |
| `{{OFFRE}}` | Site vitrine artisan clé en main, 79 €/mois sans engagement, 0 € de frais de création, hébergement OVH + HTTPS + mises à jour inclus, « maquette présentée avant mise en ligne », TVA non applicable art. 293 B CGI | page /site-vitrine-artisan/ |

Ces valeurs ne seront utilisées dans les messages que si vous les confirmez ; sinon les variables restent entre doubles accolades.
