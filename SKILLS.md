# Skills et connecteurs pour Radar & Cash

Inventaire au 14 octobre 2026 : 34 skills activés sur le compte, plus le catalogue de plugins et de connecteurs claude.ai.

## 1. Déjà installés et vraiment utiles

| Skill | Phase | Usage concret ici |
|---|---|---|
| `leads-france` | Acquisition | Listes de prospects B2B à partir des bases officielles (SIRENE, BODACC), sans clé API. Le meilleur atout pour le critère « acquisition zéro budget » sur une offre B2B française. Exemple : les entreprises créées cette semaine dans un département (elles ont besoin de site, logo, devis…). |
| `youtube-transcript` | Planner | Récupérer la transcription des vidéos « comment je gagne X € avec… » pour rétro-concevoir leur tunnel sans les regarder. |
| `deep-research` | Planner | Recherche multi-sources avec sous-agents. Puissant mais coûteux : réservé au brief du dimanche. |
| `copywriting` | Executor | Textes de la page de vente et de l'offre. |
| `page-cro` | Executor | Vérifier qu'une page de vente convertit avant d'y envoyer du trafic. |
| `launch-strategy` | Executor | Plan de lancement d'une offre validée. |
| `email-sequence` | Acquisition | Séquence d'outreach et de relance (2 à 3 e-mails). |
| `social-content` | Acquisition | Formats courts pour TikTok, Instagram, LinkedIn. |
| `marketing-psychology` | Executor | Prix, ancrage, formulation de l'offre. |
| `agent-browser` | Planner | Parcourir le tunnel d'un concurrent (pages, prix, étapes) quand une simple recherche web ne suffit pas. |
| `skill-creator` | Amélioration | Transformer `radar/PROTOCOLE.md` en skill dédié quand il sera stable (après 1 à 2 semaines de briefs). |

## 2. Installés, utiles plus tard

- `hyperframes` : générer des vidéos courtes par code. Intéressant si le canal TikTok/Reels marche.
- `ai-seo`, `seo-audit`, `content-strategy` : pour le « SEO d'opportunité » une fois une offre validée.
- `community-marketing` : si une offre se vend bien dans une communauté (WhatsApp, Telegram, Discord).
- `impeccable` : soigner le design d'une landing qui convertit déjà.
- `mcp-builder` : créer un connecteur sur mesure si un service clé n'en a pas.

## 3. À ne pas utiliser tel quel

- `veille-ia-solopreneur` : il recoupe ce projet, mais il appelle des outils `search_youtube` et `search_web` qui n'existent pas ici, il est calé sur une pile Node.js / WhatsApp / SQLite et sur des mots-clés « 2025 », et son format (newsletter IA) ne contient ni grille de score ni règle des 7 jours. Mieux vaut le remplacer par un skill « radar-cash » construit depuis `radar/PROTOCOLE.md`.
- Hors sujet pour ce projet : `daattorah-dev`, `ios-simulator-skill`, `docx`, `pptx`, `xlsx`, `pdf`, `morning`, `import-memory`.

## 4. Connecteurs déjà branchés à exploiter

- **Stripe** et **PayPal** : créer un lien de paiement en une minute et relever les ventes (la règle des 7 jours devient automatique).
- **Vercel** : mettre en ligne une page de vente en quelques minutes.
- **Gmail** : préparer les brouillons d'outreach (jamais d'envoi automatique sans validation).
- **Gamma** : générer une page web ou un document de présentation d'offre rapidement.

## 5. À ajouter (catalogue en ligne), par ordre de priorité

1. **Firecrawl** ou **Tavily** (connecteurs) : extraction web propre et recherche plus profonde que la recherche web standard. Utile pour lire des pages de vente et des marketplaces. Vérifier le palier gratuit avant d'ajouter.
2. **Plugin « Community Marketing Kit »** (communautaire) : vérifie un post avant publication sur Reddit ou un forum (règles du lieu, transparence). Évite de se faire bannir en faisant de l'acquisition gratuite.
3. **Plugin « Marketing Ideas Kit »** (communautaire) : vérifie qu'une idée peut rembourser ses clients avant de dépenser, et propose un pari principal plus deux petits tests. Colle bien avec le plafond de 20 € par test.
4. **n8n** (connecteur) : seulement quand une offre atteint 3 ventes, pour piloter les workflows depuis Claude. Demande une instance n8n (cloud payant ou auto-hébergée).
5. **Similarweb** ou **vidIQ** (connecteurs) : trafic des concurrents ou vidéos « outliers ». Bonne preuve de traction, mais vérifier le prix ; pas avant une première vente.

À éviter pour l'instant : les gros packs (« Hyper Marketing », « Windsor.ai ») orientés publicité payante, contraires au critère « acquisition zéro budget ».

## Sécurité

Un skill téléchargé depuis un annuaire en ligne exécute des instructions et parfois du code. N'installer que depuis le catalogue claude.ai ou un dépôt GitHub dont on a lu le contenu. Les annuaires publics (skillsindex.dev, claudskills.com…) recensent des dizaines de milliers de skills de qualité très variable.
