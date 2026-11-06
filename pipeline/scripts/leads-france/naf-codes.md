# Codes NAF — secteurs les plus démarchés

Format API : avec le point (ex: `62.01Z`). Plusieurs codes possibles séparés par virgule.
Liste complète : https://www.insee.fr/fr/information/2120875

⚠️ **NAF 2025** : l'INSEE déploie une nouvelle nomenclature depuis fin 2025. Les codes
ci-dessous (NAF rév. 2) restent LA clé de filtrage des APIs ; le nouveau code est fourni
en plus dans la colonne `naf_2025` du CSV (ex: 62.01Z → 62.10Y). Quand la bascule
complète aura lieu, ce fichier devra être mis à jour.

## Tech & digital
- 62.01Z Programmation informatique | 62.02A Conseil systèmes/logiciels | 63.11Z Hébergement/traitement données
- 58.29C Édition logiciels applicatifs | 63.12Z Portails internet | 62.09Z Autres activités informatiques

## Commerce & restauration
- 56.10A Restauration traditionnelle | 56.10C Restauration rapide | 56.30Z Débits de boissons
- 47.11F Hypermarchés | 47.11D Supermarchés | 47.21Z Fruits/légumes | 47.22Z Boucheries | 47.24Z Boulangeries-pâtisseries (commerce)
- 10.71C Boulangerie artisanale | 10.71D Pâtisserie
- 47.91A/B Vente à distance / e-commerce

## Beauté & bien-être
- 96.02A Coiffure | 96.02B Soins de beauté | 96.04Z Entretien corporel (spa, massage) | 93.13Z Salles de sport

## Santé
- 86.21Z Médecins généralistes | 86.22A Spécialistes | 86.23Z Dentistes | 86.90E Kinés/paramédical
- 47.73Z Pharmacies | 75.00Z Vétérinaires | 86.90F Infirmiers

## BTP & artisanat (cible RGE)
- 41.20A/B Construction bâtiments | 43.22A Plomberie | 43.22B Chauffage/clim | 43.21A Électricité
- 43.32A Menuiserie bois | 43.34Z Peinture | 43.91A Couverture | 43.99C Maçonnerie

## Immobilier & juridique & finance
- 68.31Z Agences immobilières | 68.32A Administration d'immeubles (syndics)
- 69.10Z Avocats | 69.20Z Experts-comptables | 66.22Z Courtiers assurance | 70.22Z Conseil en gestion

## Transport & logistique
- 49.32Z Taxis/VTC | 49.41A/B/C Fret routier | 53.20Z Coursiers/livraison

## Éducation & formation (cible Qualiopi)
- 85.59A Formation continue adultes | 85.59B Autres enseignements | 85.51Z Enseignement sportif | 85.52Z Enseignement culturel

## Communication & marketing (tes concurrents/partenaires)
- 73.11Z Agences de publicité | 70.21Z Relations publiques | 74.10Z Design | 74.20Z Photographie | 59.11A/B Production audiovisuelle

## Associations & cultuel
- 94.91Z Organisations religieuses | 94.99Z Autres organisations (associations) | 88.99B Action sociale
- Astuce : combiner `--association` avec `--q` (ex: `--q "communauté israelite"`, `--q synagogue`, `--q "talmud torah"`)

## Formes juridiques utiles (--forme)
- 5710 SAS | 5720 SASU | 5499 SARL | 5498 EURL | 5599/5505 SA | 1000 Entrepreneur individuel | 9220 Association déclarée | 6540 SCI
