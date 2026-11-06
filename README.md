# Clients Ici — refonte de site vitrine : site, chaîne de prospection et dossiers

Dépôt de travail de Guillaume Samama (Clients Ici, clientsici.fr). Construit le 2026-11-05.

| Dossier | Contenu |
|---|---|
| `site/` | Racine web à déployer sur l'hébergement OVH : `refonte-site-vitrine/index.html` (page d'atterrissage, gabarit du site) et `apercu/` (maquettes privées, `.htaccess` noindex). Déployé par `.github/workflows/deploy.yml` (FTP, secrets `FTP_SERVER`, `FTP_USERNAME`, `FTP_PASSWORD`). |
| `pipeline/` | Chaîne de prospection : `config.json`, `scripts/` (leads, audit, maquette, e-mail, envoi, registre), `templates/`, `data/` (file, registre, opposition), `docs/` (cadre légal, composants, tâches planifiées), `out/` (dossiers par prospect). |
| `skills/` | Copies des runbooks `prospection-run` et `prospection-replies` (à placer dans `.claude/skills/` du dépôt ou du conteneur). |
| `clientsici-site/` | Notes de livraison et tests de la page d'atterrissage. |
| `_preparation/` | Environnement, analyse « même site ou site dédié », hébergement des maquettes. |

Chemin du pipeline pour les sessions planifiées : `<clone>/pipeline` (les scripts calculent leurs chemins relativement à eux-mêmes). Amorçage d'un conteneur neuf : `bash pipeline/scripts/bootstrap.sh`.

Règles non négociables : `pipeline/docs/00-cadre.md`. Aucun envoi hors mode `auto` ; registre et liste d'opposition font foi.
