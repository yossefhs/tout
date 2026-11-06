# 04 — Livraison du système (état au 2026-11-05, fin de session de construction)

## Ce qui existe et a été testé

| Élément | Emplacement | État |
|---|---|---|
| Page d'atterrissage `/refonte-site-vitrine/` (gabarit du site) | `site/refonte-site-vitrine/index.html` | testée (34 contrôles, Lighthouse 100/100/100/100), **non publiée** |
| Chaîne de prospection : leads SIRENE → enrichissement site/e-mail → filtre TPE → audit automatique → maquette → e-mail → envoi/brouillon → registre | `pipeline/` | testée de bout en bout sur deux leads réels sans envoi ; 43 tests unitaires OK |
| Runbooks des sessions planifiées | `.claude/skills/prospection-run`, `prospection-replies` (copies dans `skills/`) | relus, cohérents avec les scripts |
| Tâches planifiées | `trig_01XihSK66juWho9BrnngLJdK` (quotidienne 09:37), `trig_01LQguwkxHCYSceLFzKMVWQf` (réponses 11:23/14:23) | créées, **en pause** |
| Déploiement | `.github/workflows/deploy.yml`, `site/apercu/.htaccess` | écrit, **non testé** (aucun accès FTP ni dépôt) |
| Exemple de dossier prospect complet | `prospects/rabarot-freres.fr/` | audit, maquette, captures, tests, messages |

## Ce qui est bloqué et pourquoi

1. **Mise en ligne sur clientsici.fr** : aucun accès à l'hébergement OVH depuis cette session. Voies : (a) dossier du Mac partagé par Remote Control (fichiers d'accès déjà présents) → envoi FTP depuis le Mac ; (b) dépôt GitHub + secrets FTP → déploiement automatique par le workflow.
2. **Persistance des sessions planifiées** : conteneur éphémère ; le rattachement de `yossefhs/tout` a été refusé par le classificateur de permissions de cette session. Voies : autoriser `add_repo` (règle de permission) ou créer un dépôt dédié et l'attacher ; puis pousser ce dossier sur la branche `clientsici-prospection`.
3. **Connecteur Gmail dans les tâches planifiées** : non transmis par l'outil de création ; recréer les deux tâches depuis l'interface claude.ai avec le connecteur du compte d'envoi. Le connecteur actuel n'a pas la permission de créer des libellés.
4. **Expéditeur** : le connecteur Gmail envoie depuis le compte Google connecté (yossefhs@gmail.com). Pour guillaume@clientsici.fr : Brevo (clé API injectée par secret réseau `api.brevo.com`, en-tête `api-key`, SPF/DKIM chez OVH) ou SMTP OVH depuis le Mac. Réponses : rediriger contact@/guillaume@ vers la boîte Gmail connectée.

## Décisions qui vous reviennent (config.json)

mode (`review` par défaut) ; `envoi.fournisseur` (`gmail-draft` | `brevo` | `smtp`) ; plafonds (10/jour, 4/heure ; 5/jour conseillé la première semaine) ; départements (28 seul) ; codes NAF (43.91A charpente vs 43.91B couverture) ; `cible_tpe` (≤ 19 salariés, CA ≤ 2 M€, ≤ 2 établissements) ; webmails acceptés ; `maquette_lien_dans_email` (false tant que `/apercu/` n'est pas en ligne) ; relances (désactivées) ; réponses automatiques (`jamais`).

## Rendement mesuré

Eure-et-Loir, artisans + commerces, 110 leads enrichis → 7 avec site vérifié et e-mail → 3 après filtre TPE. Environ 6 % des leads enrichis sont exploitables ; la majorité des artisans du 28 n'ont pas de site propre (candidats à l'offre « création », non traités par cette chaîne). Compter 150 à 200 leads enrichis (4 à 5 min) pour 10 dossiers par jour, et 1 h à 1 h 15 de session quotidienne.
