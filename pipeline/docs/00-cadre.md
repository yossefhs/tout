# 00 — Cadre : règles CNIL/RGPD, délivrabilité, modes de fonctionnement, décisions à prendre

Composant D de la chaîne de prospection « Clients Ici » (Guillaume Samama, micro-entrepreneur, clientsici.fr). Ce document fixe ce que les sessions planifiées (`/prospection-run`, `/prospection-replies`) ont le droit de faire, et ce qui reste à décider par Guillaume. Rédigé le 2026-11-05 ; les repères juridiques sont ceux publiés par la CNIL pour la prospection commerciale entre professionnels et ne remplacent pas un conseil juridique.

## 1. Prospection B2B par e-mail : ce que la chaîne respecte

| Règle | Fondement (repère) | Mise en œuvre dans la chaîne |
|---|---|---|
| **Information de la personne et droit d'opposition dans chaque message** | RGPD art. 13/14 et 21 ; L. 34-5 CPCE (prospection entre professionnels admise sans consentement préalable si l'objet est en rapport avec la profession et que l'opposition est possible à tout moment, simplement et gratuitement) | `build_email.py` ajoute un bloc fixe : « Pourquoi ce message : vos coordonnées viennent de votre site <domaine>, qui est public. Pour ne plus recevoir de message, répondez STOP et je vous retire de ma liste. Confidentialité : https://clientsici.fr/confidentialite/ ». La page `/refonte-site-vitrine/` reprend la même information (« Vous avez reçu un e-mail de ma part ? ») |
| **Pertinence avec l'activité professionnelle** | Base légale : intérêt légitime (art. 6.1.f), à condition que l'offre soit en rapport avec la fonction ou l'activité du destinataire | Cible = entreprises actives (SIRENE) des codes NAF retenus ; l'e-mail porte sur **leur** site, avec un constat précis relevé dessus (`audit.json`) ; aucun e-mail si le verdict d'audit n'est pas « refonte pertinente » ou « amélioration ciblée préférable » |
| **Adresses professionnelles, pas d'adresse nominative sans lien avec la fonction** | Recommandations CNIL prospection B2B : une adresse générique (`contact@`) ou une adresse nominative d'une personne dans sa fonction professionnelle ; jamais une adresse personnelle sans rapport | `filter_queue.py` : seuls les e-mails du domaine du site, d'un domaine portant le nom de l'entreprise, ou d'un webmail utilisé comme adresse de l'entreprise sont retenus ; les adresses manifestement personnelles et les adresses de tiers (hébergeur, agence, annuaire) sont écartées (`docs/01-leads.md` § 2). La relecture du runbook le revérifie avant chaque brouillon |
| **Collecte loyale, sources publiques** | Art. 5 et 14 (information sur la source) | Sources : API Recherche d'entreprises (open data), site de l'entreprise (lecture seule, User-Agent identifiable). Jamais LinkedIn, Google Maps, Pages Jaunes, formulaires, espaces d'administration |
| **Registre d'opposition** | Obligation de prendre en compte l'opposition sans délai et de ne plus solliciter | `data/opposition.csv` (`valeur;type;date;source`) alimenté par `ledger.py stop` dès qu'une réponse STOP ou un bounce est lu ; appliqué à la collecte (`filter_queue.py`), au runbook (`ledger.py check`) et à l'ajout au registre (`ledger.py add` refuse). Une opposition sur une adresse du domaine propre vaut pour tout le domaine |
| **Un seul contact, pas de harcèlement** | Proportionnalité ; CNIL : limiter la pression commerciale | Un e-mail par domaine, jamais deux ; relances **désactivées** (`relance.activee: false`) ; si Guillaume les active : 1 relance au plus, après 7 jours, jamais après une réponse quelle qu'elle soit |
| **Conservation limitée** | Art. 5.1.e ; repère CNIL : données de prospects non clients conservées au plus 3 ans après le dernier contact | `data/raw/*` (extractions brutes) : purge conseillée à 90 jours ; `ledger.csv` : conserver les lignes `stop`/`bounced` (preuve de prise en compte de l'opposition) sans limite, purger les autres lignes 3 ans après la date ; `out/<jour>/<domaine>/` (audits, captures, maquettes) : supprimer sur demande du prospect et au plus tard 3 ans après |
| **Données de dirigeants** | Minimisation | Nom et fonction issus du RNE (publics), uniquement pour la civilité ; aucune autre donnée personnelle |
| **Maquette non sollicitée** | Loyauté, pas d'indexation | Lien privé `/apercu/<jeton>/` avec `noindex` et pas de listage ; suppression sur demande (`publish_maquette.py --supprimer`) ; la page d'atterrissage le dit |
| **Droits des personnes** | Art. 15 à 21 | Toute demande d'accès/effacement lue par `/prospection-replies` est signalée à Guillaume dans le rapport ; réponse sous un mois |

Ce que la chaîne **ne fait pas** et ne doit pas faire : prospection de particuliers (B2C : consentement préalable requis), SMS ou WhatsApp automatisés (les textes `whatsapp`/`sms` de `build_email.py` sont marqués « brouillon : conditions de contact à vérifier » et ne sont jamais envoyés), appels, achat de fichiers, pixel de suivi.

## 2. Délivrabilité

Repères issus du skill `cold-email` (`references/deliverability.md`) et des règles Google/Yahoo/Microsoft 2024-2025.

1. **Domaine d'envoi.** Ne pas prospecter depuis le domaine principal `clientsici.fr` (celui des clients, des factures, de la page d'atterrissage) ni depuis un Gmail personnel. Recommandation : un **domaine secondaire** évidemment lié (ex. `clientsici.net`, `clients-ici.fr`), redirigé vers clientsici.fr, avec une boîte Google Workspace nominative (`guillaume@…`) ; `Reply-To` et signature vers `contact@clientsici.fr`. Tant que la décision n'est pas prise, la session utilise **le compte Gmail connecté au connecteur** : c'est l'adresse d'envoi de fait, et la raison pour laquelle le mode `review` est le défaut.
2. **Authentification** du domaine d'envoi : SPF, DKIM, DMARC (`p=none` avec rapports pour commencer, puis `p=quarantine`), alignés sur le domaine `From`. Vérifier avant le premier envoi (ex. `dig TXT _dmarc.<domaine>`).
3. **Montée en volume** (boîte neuve ou peu utilisée) : semaine 1 : 5 e-mails/jour ; semaine 2 : 10/jour ; semaine 3 et au-delà : 20/jour **au maximum**. `plafond_quotidien` et `plafond_horaire` sont les garde-fous ; ne les monter qu'à la main, dans `config.json`. Les réponses envoyées comptent dans le volume. Une boîte neuve gagne à recevoir et envoyer d'abord de vrais échanges pendant 2 à 3 semaines.
4. **Texte brut, court, varié** : `build_email.py` produit 80 à 110 mots (compteur interne, voir `docs/03` § 2), un ou deux constats sans chiffre ni score d'outil, une seule question, formulations tirées au sort par domaine (pas deux e-mails identiques), ligne d'opposition et adresse postale.
5. **Pas d'ouverture suivie, pas de lien suivi** : les ouvertures sont inutiles (Apple Mail Privacy Protection) et le pixel est un signal de spam. On mesure les **réponses** (`ledger.csv`).
6. **Liste propre** : e-mails validés par MX avant d'entrer en file ; bounces inscrits en opposition (`type bounce`). Objectif : taux de bounce < 2 %.
7. **Arrêt** (à appliquer par Guillaume, les sessions le signalent) : plaintes « spam » ou STOP agressifs ≥ 1 sur 100 envois → pause et révision du ciblage ; taux de réponse < 1 % après 300 envois → arrêt, l'offre ou la cible est à revoir ; domaine sur une liste noire → arrêt immédiat de la boîte.
8. **Surveillance hebdomadaire** : Google Postmaster Tools sur le domaine d'envoi (réputation, plaintes), rapports DMARC, lecture du registre (`ledger.py list`).

## 3. Mode `review` et mode `auto`

| | `mode: "review"` (défaut) | `mode: "auto"` |
|---|---|---|
| E-mails de prospection | `mcp__Gmail__create_draft` : brouillons dans le compte Gmail, à relire et envoyer par Guillaume | `mcp__Gmail__send_message` puis libellé `Prospection` |
| Compte dans les plafonds | les brouillons créés dans la journée | les envois de la journée |
| Fenêtre horaire (`heures_envoi`) | informative : des brouillons peuvent être préparés à toute heure | bloquante : rien hors 09:00–18:00 Europe/Paris, jours ouvrés |
| Réponses aux prospects (`/prospection-replies`) | toujours des brouillons dans le fil | selon `reponses_auto` : `jamais` (défaut, brouillons), `accuse_reception` (une phrase envoyée + brouillon complet), `complet` (réponse envoyée) |
| Accusé de STOP | brouillon si `accuser_reception_stop: true` | envoyé si `accuser_reception_stop: true` et `reponses_auto ≠ jamais` |
| Registre | `drafted` + `draft_id` | `sent` + `thread_id` |

Dans les deux modes : mêmes règles de registre, d'opposition, de plafonds, de relecture, de contenu ; le lien vers la maquette n'apparaît dans l'e-mail que si `maquette_lien_dans_email: true`.

Passer en `auto` suppose : une adresse d'envoi dédiée et authentifiée (§ 2.1–2.2), une semaine de `review` sans correction de fond sur les brouillons, et la persistance en place (§ 4, point 5) : sans registre persistant, une session `auto` peut réécrire au même domaine.

## 4. Décisions à prendre par Guillaume

1. **Adresse d'expédition** : rester sur le Gmail connecté (adresse de fait, acceptable pour quelques brouillons/jour en `review`) ou créer un domaine secondaire + boîte dédiée (recommandé avant tout `auto`) ; dans ce cas, connecter cette boîte au connecteur Gmail des tâches planifiées et renseigner `expediteur.email_reponse` (adresse de réponse souhaitée).
2. **Mode** : `review` (défaut) ou `auto` ; et pour les réponses : `reponses_auto` (`jamais` par défaut) et `accuser_reception_stop` (`false` par défaut).
3. **Plafonds et fenêtre** : `plafond_quotidien` (10), `plafond_horaire` (4), `heures_envoi` (09:00–18:00, lundi–vendredi) ; montée en volume § 2.3.
4. **Départements et codes NAF** : `depts` (28 ; voisins : 27, 61, 72, 41, 45, 91, 78), `nafs_artisans` (43.91A « charpente » annoncé comme couverture dans le skill : la couverture est 43.91B), `nafs_commerces`.
5. **Dépôt GitHub** pour la persistance et le déploiement : le conteneur des sessions est éphémère ; sans dépôt attaché contenant `/home/user/refonte-vitrine/pipeline` (au moins `config.json`, `data/`, `out/`) et `site/` (aperçus de maquettes), chaque exécution repart de zéro et les aperçus ne sont jamais mis en ligne. Voir `docs/04-taches-planifiees.md` § 3 et `deploy/.github-workflows-deploy.yml` (secrets FTP OVH à créer).
6. **Lien maquette dans l'e-mail** : `maquette_lien_dans_email` reste `false` jusqu'à ce qu'une maquette test soit accessible à son URL `/apercu/<jeton>/` (déploiement vérifié), puis `true`.
7. **Relances** : laisser désactivées (`relance.activee: false`) ou activer (1 relance à 7 jours, jamais après réponse).
8. **Conservation** : valider les durées du § 1 (90 jours pour `data/raw`, 3 ans pour les dossiers de prospects) et qui purge.
9. **Mentions légales et politique de confidentialité** de clientsici.fr : vérifier qu'elles mentionnent la prospection B2B, la base légale (intérêt légitime), la source des données (sites publics, registres), les durées de conservation et l'adresse pour exercer ses droits (`contact@clientsici.fr`) ; `build_email.py` renvoie vers https://clientsici.fr/confidentialite/.
