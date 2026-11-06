# Audit du site www.gre-enr.fr

URL auditée : https://www.gre-enr.fr/ · Date : 2026-11-05T21:33:36+00:00 · Outil : audit_site.py (requests + Playwright + Lighthouse 12), lecture seule, User-Agent « Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/) ».

## Synthèse

**Verdict : refonte pertinente** (1 constat(s) de gravité haute et 2 moyenne(s)).
8 constats : 1 de gravité haute, 2 moyenne, 5 basse ; 5 page(s) consultée(s).
Lighthouse mobile (2026-11-05T21:34:05+00:00) : performance 25/100, accessibilité 85, bonnes pratiques 75, SEO 85 ; LCP 11541 ms, CLS 0.07, TBT 2794 ms.
Mobile 375 px (Playwright) : pas de débordement, 185 requêtes, 15.32 Mo, 8.01 s jusqu'à networkidle.
Points bloquants : Performance mobile faible (Lighthouse).

## Ce qui fonctionne

- HTTPS actif et redirection http→https en place
- Variante www / sans www redirigée correctement
- Balise viewport présente
- Aucun débordement horizontal à 375 px
- Titre présent (41 caractères)
- H1 unique : « GROUPE ROY ÉNERGIE Installateur de panneaux photovoltaïques »
- Numéro cliquable (tel:) présent : tel:02 38 801 801
- Ville ou zone d'intervention visible sur l'accueil (zone mentionnée : Ain, Aisne, Allier, Alpes-de-Haute-Provence, Hautes-Alpes)
- Sitemap présent (https://www.gre-enr.fr/sitemap_index.xml, 9 sous-sitemaps URL)
- robots.txt présent et non bloquant

## Actions prioritaires

1. **Performance mobile faible (Lighthouse)** (haute) : Réduire le poids des images, limiter les scripts et polices, servir le site depuis un hébergement rapide avec cache.
2. **Page d'accueil lourde sur mobile** (moyenne) : Compresser et redimensionner les images (WebP), supprimer les scripts inutiles, activer la mise en cache.
3. **Bouton d'appel non visible sans défiler à 375 px** (moyenne) : Placer un bouton « Appeler » dans l'en-tête ou une barre fixe en bas d'écran sur mobile.
4. **Erreurs JavaScript ou ressources en échec au chargement** (basse) : Corriger ou retirer les scripts en erreur ; vérifier les fichiers manquants (404).
5. **Meta description trop longue** (basse) : Ramener à 120–155 caractères.
6. **Images sans attribut alt** (basse) : Décrire chaque photo en une phrase (ex. « Pose de carrelage, cuisine à Chartres »).
7. **Données structurées LocalBusiness absentes** (basse) : Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google.
8. **Année de copyright ancienne (indice de site non mis à jour)** (basse) : Mettre l'année à jour automatiquement ou la retirer.

## Constats détaillés

| Priorité | Problème | Preuve | Conséquence possible | Correction |
|---|---|---|---|---|
| haute | Performance mobile faible (Lighthouse) (mesure) | https://www.gre-enr.fr/ — performance 25/100, LCP 11541 ms, CLS 0.07, TBT 2794 ms (Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T21:34:05+00:00) | La page s'affiche lentement sur téléphone ; les visiteurs venus de Google Maps repartent avant d'avoir vu le numéro. | Réduire le poids des images, limiter les scripts et polices, servir le site depuis un hébergement rapide avec cache. |
| moyenne | Page d'accueil lourde sur mobile (mesure) | https://www.gre-enr.fr/ — 15.3 Mo transférés, 185 requêtes (Playwright, 2026-11-05T21:33:43+00:00) | Chargement long en 4G ou en zone mal couverte ; une partie des visiteurs part avant l'affichage. | Compresser et redimensionner les images (WebP), supprimer les scripts inutiles, activer la mise en cache. |
| moyenne | Bouton d'appel non visible sans défiler à 375 px (mesure) | https://www.gre-enr.fr/ — lien tel: présent mais hors du premier écran mobile (Playwright, 2026-11-05T21:33:43+00:00) | Le visiteur pressé ne voit pas comment appeler sans défiler. | Placer un bouton « Appeler » dans l'en-tête ou une barre fixe en bas d'écran sur mobile. |
| basse | Erreurs JavaScript ou ressources en échec au chargement (mesure) | https://www.gre-enr.fr/ — 3 erreur(s) console à 375 px, ex. : Failed to load resource: the server responded with a status of 400 (Bad Request) | Des fonctions (menu, formulaire, carrousel) peuvent ne pas marcher chez certains visiteurs. | Corriger ou retirer les scripts en erreur ; vérifier les fichiers manquants (404). |
| basse | Meta description trop longue (fait observé) | https://www.gre-enr.fr/ — 218 caractères | L'extrait est tronqué dans les résultats. | Ramener à 120–155 caractères. |
| basse | Images sans attribut alt (fait observé) | https://www.gre-enr.fr/ — 195 image(s) sans alt sur 5 page(s) consultée(s) (accueil : 109/198) | Photos de chantiers invisibles pour Google Images et les lecteurs d'écran. | Décrire chaque photo en une phrase (ex. « Pose de carrelage, cuisine à Chartres »). |
| basse | Données structurées LocalBusiness absentes (fait observé) | https://www.gre-enr.fr/ — types JSON-LD trouvés : AggregateRating, Brand, BreadcrumbList, EntryPoint, ImageObject, ListItem, Organization, Person, PropertyValueSpecification, Rating, ReadAction, Review, SearchAction, WebPage, WebSite | Google doit deviner nom, adresse, téléphone et horaires au lieu de les lire. | Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google. |
| basse | Année de copyright ancienne (indice de site non mis à jour) (fait observé) | https://www.gre-enr.fr/ — © 2024 (année courante 2026) | Le visiteur peut croire que l'entreprise n'est plus active. | Mettre l'année à jour automatiquement ou la retirer. |

## Mesures et conditions

- HTTP (requests, 2026-11-05T21:33:36+00:00) : URL demandée https://grouperoyenergie.com → finale https://www.gre-enr.fr/ ; chaîne : 301 https://grouperoyenergie.com/ ; HSTS : absent.
- Test http:// : http://www.gre-enr.fr/ → https://www.gre-enr.fr/ (status 200).
- Test variante www : https://gre-enr.fr/ → https://www.gre-enr.fr/ (status 200).
- robots.txt : présent (status 200).
- sitemap : https://www.gre-enr.fr/sitemap_index.xml (index, 9 sous-sitemaps URL ; sans exploration exhaustive).
- Navigateur mobile 375x812 (Playwright Chromium, 2026-11-05T21:33:43+00:00) : status 200, 8.01 s jusqu'à networkidle, 185 requêtes, 15.32 Mo, 3 erreur(s) console, largeur défilable 375 px, plus petit texte 14 px.
  Captures : captures/mobile-375-fold.png, captures/mobile-375-full.png.
- Navigateur desktop 1440x900 (Playwright Chromium, 2026-11-05T21:33:43+00:00) : status 200, 6.6 s jusqu'à networkidle, 167 requêtes, 16.00 Mo, 3 erreur(s) console, largeur défilable 1440 px, plus petit texte 13 px.
  Captures : captures/desktop-1440-fold.png, captures/desktop-1440-full.png.
- Lighthouse : Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T21:34:05+00:00, URL https://www.gre-enr.fr/ ; mesure unique depuis un serveur (pas un téléphone réel), réseau et CPU simulés ; les valeurs varient d'une mesure à l'autre ; rapport : lighthouse.json.

## Pages consultées

| Rôle | URL | Status | Title (longueur) | Description (longueur) | H1 | tel: | Images sans alt |
|---|---|---|---|---|---|---|---|
| accueil | https://www.gre-enr.fr/ | 200 | GROUPE ROY ÉNERGIE, expert photovoltaïque (41) | 218 | 1 | 3 | 109/198 |
| contact | https://www.gre-enr.fr/contact/ | 200 | Vous avez un projet photovoltaïque ? Contactez-nous ! / Grou (74) | 117 | 1 | 3 | 18/96 |
| realisations | https://www.gre-enr.fr/realisations/ | 200 | Nos Réalisations photovoltaïques / Groupe Roy Énergie (53) | 133 | 1 | 3 | 18/20 |
| services | https://www.gre-enr.fr/emploi-photovoltaique/ | 200 | Recrutement photovoltaïque / Groupe Roy Énergie (47) | 129 | 1 | 3 | 28/30 |
| tarifs | https://www.gre-enr.fr/revente-delectricite#prix_rachat_electricite | 200 | Revente d'électricité photovoltaïque / Groupe Roy Énergie (57) | 140 | 1 | 3 | 22/42 |

## Risques de refonte et éléments à préserver

Inventaire limité aux 5 page(s) consultée(s) ; le site peut en compter davantage (sitemap : nombre inconnu). Toute page non listée ici doit être inventoriée avant mise en ligne, et chaque ancienne adresse redirigée (301).

- Pages trouvées : accueil → https://www.gre-enr.fr/ (200); contact → https://www.gre-enr.fr/contact/ (200); realisations → https://www.gre-enr.fr/realisations/ (200); services → https://www.gre-enr.fr/emploi-photovoltaique/ (200); tarifs → https://www.gre-enr.fr/revente-delectricite#prix_rachat_electricite (200)
- Menu : Dépannage et Maintenance, Tarifs de rachat, Recrutement, Point conseil, Le Groupe, Nos engagements RSE, Nos Partenariats, Comprendre le photovoltaïque, Autoconsommation, Revente totale, Location de toiture, Calculer vos économies, Tarif de rachat, Agriculteur, Industriel et tertiaire
- Coordonnées relevées : téléphones 05 20 26 09 15, 02 38 46 15 67, 02 38 80 18 01 ; e-mails contact@gre-enr.fr ; adresses 23 rue Gondrelier Z.A de la Haute Borne, 28310 TOURY Itinéraire; 28250 Digny; 28157 Fontenay-sur-Conie.
- Services listés (titres H2/H3, à vérifier) : Ensemble,, NOS SOLUTIONS, Ils nous font confiance, GROUPE ROY ÉNERGIE vous accompagne de A à Z dans votre projet, Réalisations, Pilotage de charges énergétique : optimisez vos coûts, GROUPE ROY ÉNERGIE DÉMOCRATISE LE PHOTOVOLTAÏQUE, Rejoignez un groupe en forte croissance, Vos coordonnées, Informations sur votre projet, Nom et prénom de la personne qui vous a recommandé Groupe Roy Énergie, Demander une étude personnalisée, OBTENEZ VOTRE RENDEZ-VOUS PERSONNALISÉ À DISTANCE, Nous sommes à votre écoute, En vidéo
- Technologie détectée : WordPress 7.1.4.
- Risques : perte de pages non inventoriées, de l'historique Google si les redirections manquent, de formulaires ou d'espaces clients non visibles dans cet audit ; coordonnées à vérifier avec la fiche Google avant reprise.

## Verdict motivé

**refonte pertinente** : 1 constat(s) de gravité haute et 2 moyenne(s). Règle : « refonte pertinente » si ≥ 2 constats hauts ou 1 haut + 2 moyens ; « amélioration ciblée préférable » si ≥ 2 moyens sans haut ; « informations insuffisantes » si la page n'a pas pu être chargée ou moins de 3 constats fiables ; sinon « aucune amélioration substantielle établie ».
