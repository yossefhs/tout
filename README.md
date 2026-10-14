# Radar & Cash

Poste de pilotage pour détecter des business en ligne qui rapportent déjà, les répliquer vite, et abandonner sans regret ce qui ne vend pas en 7 jours.

## Comment ça marche

- Chaque jour (dimanche → vendredi, 12h15 heure de Jérusalem), une session Claude lit [`radar/PROTOCOLE.md`](radar/PROTOCOLE.md), fait la recherche, met à jour le registre et écrit le brief du jour dans `briefs/`.
- Le brief arrive par notification et par e-mail vers 12h30.
- Pour améliorer le brief, on modifie `radar/PROTOCOLE.md` ou `radar/GRILLE.md`, pas la tâche planifiée.

## Fichiers

| Fichier | Rôle |
|---|---|
| [`radar/GRILLE.md`](radar/GRILLE.md) | Les 5 critères de score et les règles (7 jours, budget, légal) |
| [`radar/PROTOCOLE.md`](radar/PROTOCOLE.md) | Les instructions suivies chaque jour par la session Claude |
| [`radar/registre.json`](radar/registre.json) | Toutes les opportunités : repérées, en test, validées, tuées |
| [`briefs/`](briefs/) | Un Daily Cash Brief par jour (`AAAA-MM-JJ.md`) |
| [`SKILLS.md`](SKILLS.md) | Les skills et connecteurs utiles pour ce projet |

## Signaler une vente ou un lancement

Dis-le simplement à Claude dans une session (« j'ai lancé X aujourd'hui », « 2 ventes sur X ») : il met à jour `radar/registre.json`. Si Stripe ou PayPal sont connectés à la session du brief, les ventes passées par leurs liens de paiement sont relevées automatiquement.
