# Audit du site rabarot-freres.fr

URL auditée : https://rabarot-freres.fr/ · Domaine demandé : rabarot-freres.fr · Domaine final : rabarot-freres.fr · Date : 2026-11-05T21:58:59+00:00 · Outil : audit_site.py (requests + Playwright + Lighthouse 12), lecture seule, User-Agent « Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/) ».

## Synthèse

**Verdict : refonte pertinente** (1 constat(s) de gravité haute et 2 moyenne(s)).
6 constats : 1 de gravité haute, 2 moyenne, 3 basse ; 5 page(s) consultée(s).
Lighthouse mobile (2026-11-05T21:59:11+00:00) : performance 75/100, accessibilité 84, bonnes pratiques 96, SEO 92 ; LCP 6873 ms, CLS 0.025, TBT 42 ms.
Mobile 375 px (Playwright) : débordement horizontal, 50 requêtes, 2.28 Mo, 2.18 s jusqu'à networkidle.
Points bloquants : Débordement horizontal à 375 px.

## Ce qui fonctionne

- HTTPS actif et redirection http→https en place
- En-tête HSTS présent (le navigateur force HTTPS après la première visite)
- Balise viewport présente
- Aucune erreur console au chargement mobile
- Lighthouse SEO technique 92/100
- Lighthouse bonnes pratiques 96/100
- Titre présent (51 caractères)
- Meta description présente (153 caractères)
- Numéro cliquable (tel:) présent : tel:02 37 99 52 16
- Ville ou zone d'intervention visible sur l'accueil (ville « GOMMERVILLE » trouvée sur l'accueil)
- Données structurées LocalBusiness présentes (LocalBusiness)
- Copyright à jour (© 2025)
- Sitemap présent (https://www.rabarot-freres.fr/sitemap.xml, 23 URL)
- robots.txt présent et non bloquant

## Actions prioritaires

1. **Débordement horizontal à 375 px** (haute) : Corriger les éléments plus larges que l'écran (images, tableaux, blocs à largeur fixe) avec max-width:100 % et une mise en page fluide.
2. **Performance mobile moyenne (Lighthouse)** (moyenne) : Optimiser images et scripts ; viser un LCP sous 2,5 s.
3. **Aucun bouton de contact visible sans défiler à 375 px** (moyenne) : Placer un bouton « Appeler » dans l'en-tête ou une barre fixe en bas d'écran sur mobile.
4. **Versions avec et sans « www » servies toutes deux** (basse) : Rediriger (301) l'une des deux versions vers l'autre.
5. **Plusieurs titres H1 sur l'accueil** (basse) : Garder un seul H1, passer les autres en H2.
6. **Images sans attribut alt** (basse) : Décrire chaque photo en une phrase avec le métier et le lieu (ex. « Maçon à Gommerville : [ce que montre la photo] »).

## Constats détaillés

| Priorité | Problème | Preuve | Conséquence possible | Correction |
|---|---|---|---|---|
| haute | Débordement horizontal à 375 px (mesure) | https://rabarot-freres.fr/ — largeur défilable 768 px pour un écran de 375 px (Playwright, 2026-11-05T21:59:01+00:00) | Sur téléphone, une partie du contenu sort de l'écran ; textes et boutons peuvent être coupés, et il faut défiler sur le côté. | Corriger les éléments plus larges que l'écran (images, tableaux, blocs à largeur fixe) avec max-width:100 % et une mise en page fluide. |
| moyenne | Performance mobile moyenne (Lighthouse) (mesure) | https://rabarot-freres.fr/ — performance 75/100, LCP 6873 ms, CLS 0.025, TBT 42 ms (Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T21:59:11+00:00) | L'affichage peut être perceptiblement lent sur un réseau mobile ordinaire. | Optimiser images et scripts ; viser un LCP sous 2,5 s. |
| moyenne | Aucun bouton de contact visible sans défiler à 375 px (mesure) | https://rabarot-freres.fr/ — lien tel: présent plus bas dans la page, mais aucun lien d'appel ni bouton de contact sur le premier écran mobile (Playwright, 2026-11-05T21:59:01+00:00) | Le visiteur pressé risque de ne pas voir comment appeler sans défiler. | Placer un bouton « Appeler » dans l'en-tête ou une barre fixe en bas d'écran sur mobile. |
| basse | Versions avec et sans « www » servies toutes deux (fait observé) | https://www.rabarot-freres.fr/ — réponse 200 sur https://www.rabarot-freres.fr/ sans redirection vers https://rabarot-freres.fr/ | Deux adresses pour le même contenu : Google peut hésiter sur la version à afficher. | Rediriger (301) l'une des deux versions vers l'autre. |
| basse | Plusieurs titres H1 sur l'accueil (fait observé) | https://rabarot-freres.fr/ — 5 balises <h1> | La hiérarchie des titres peut en être brouillée. | Garder un seul H1, passer les autres en H2. |
| basse | Images sans attribut alt (fait observé) | https://rabarot-freres.fr/ — 38 image(s) sans alt sur 5 page(s) consultée(s) (accueil : 19/19) | Ces photos risquent de ne pas remonter dans Google Images et restent muettes pour les lecteurs d'écran. | Décrire chaque photo en une phrase avec le métier et le lieu (ex. « Maçon à Gommerville : [ce que montre la photo] »). |

## Mesures et conditions

- HTTP (requests, 2026-11-05T21:58:59+00:00) : URL demandée https://rabarot-freres.fr → finale https://rabarot-freres.fr/ ; chaîne : aucune redirection ; HSTS : max-age=31536000; preload.
- Test http:// : http://rabarot-freres.fr/ → https://rabarot-freres.fr/ (status 200).
- Test variante www : https://www.rabarot-freres.fr/ → https://www.rabarot-freres.fr/ (status 200).
- robots.txt : présent (status 200).
- sitemap : https://www.rabarot-freres.fr/sitemap.xml (urlset, 23 URL ; sans exploration exhaustive).
- Navigateur mobile 375x812 (Playwright Chromium, 2026-11-05T21:59:01+00:00) : status 200, 2.18 s jusqu'à networkidle, 50 requêtes, 2.28 Mo, 0 erreur(s) console, largeur défilable 768 px, plus petit texte 14 px.
  Captures : captures/mobile-375-fold.png, captures/mobile-375-full.png.
- Navigateur desktop 1440x900 (Playwright Chromium, 2026-11-05T21:59:01+00:00) : status 200, 1.71 s jusqu'à networkidle, 53 requêtes, 2.30 Mo, 0 erreur(s) console, largeur défilable 1440 px, plus petit texte 14 px.
  Captures : captures/desktop-1440-fold.png, captures/desktop-1440-full.png.
- Lighthouse : Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T21:59:11+00:00, URL https://rabarot-freres.fr/ ; mesure unique depuis un serveur (pas un téléphone réel), réseau et CPU simulés ; les valeurs varient d'une mesure à l'autre ; rapport : lighthouse.json.

## Pages consultées

| Rôle | URL | Status | Title (longueur) | Description (longueur) | H1 | tel: | Images sans alt |
|---|---|---|---|---|---|---|---|
| accueil | https://rabarot-freres.fr/ | 200 | Rabarot Frères - Couvreur RGE Qualibat à Angerville (51) | 153 | 5 | 0 | 19/19 |
| contact | https://rabarot-freres.fr/contact | 200 | Contact (7) | 0 | 1 | 1 | 3/3 |
| a-propos | https://rabarot-freres.fr/a-propos | 200 | a-propos (8) | 0 | 4 | 0 | 4/4 |
| navigation | https://rabarot-freres.fr/agrandissement-maison | 200 | Agrandissement de maison (24) | 0 | 4 | 0 | 8/8 |
| navigation | https://rabarot-freres.fr/cloture | 200 | Terrassement à Angerville - Aménagement de terrain (50) | 153 | 4 | 0 | 4/4 |

## Risques de refonte et éléments à préserver

Inventaire limité aux 5 page(s) consultée(s) ; le site peut en compter davantage (sitemap : 23). Toute page non listée ici doit être inventoriée avant mise en ligne, et chaque ancienne adresse redirigée (301).

- Pages trouvées : accueil → https://rabarot-freres.fr/ (200); contact → https://rabarot-freres.fr/contact (200); a-propos → https://rabarot-freres.fr/a-propos (200); navigation → https://rabarot-freres.fr/agrandissement-maison (200); navigation → https://rabarot-freres.fr/cloture (200)
- Menu : Accueil, Maçonnerie, Agrandissement de maison, Ravalement, Terrassement, Couverture zinguerie, installation-toiture, renovation-toiture, demoussage, fenetre-toit, renovation-charpente, Platrerie-isolation, Pose-cloisons, faux-plafond, Carrelage faîence
- Coordonnées relevées : téléphones 02 37 99 52 16 ; e-mails rabarot-freres@orange.fr ; adresses 3 Rue du Château, 28310 Gommerville.
- Services listés (listes de prestations et titres H2/H3, à vérifier) : Entreprise familiale, RGE Qualibat, Garantie décennale, Écoute et proximité, Couverture, Menuiseries, Clôtures, Extension, Charpente, Plâtrerie, Fenêtre de toit, Maçonnerie
- Correspondance avec le lead : retrouvés : nom (« RABAROT FRERES », https://rabarot-freres.fr/) ; ville (« GOMMERVILLE », https://rabarot-freres.fr/) ; cp (« 28310 », https://rabarot-freres.fr/) ; non retrouvés : siren (« 500467279 »).
- Technologie détectée : Duda.
- Risques : perte de pages non inventoriées, de l'historique Google si les redirections manquent, de formulaires ou d'espaces clients non visibles dans cet audit ; coordonnées à vérifier avec la fiche Google avant reprise.

## Verdict motivé

**refonte pertinente** : 1 constat(s) de gravité haute et 2 moyenne(s). Règle : « refonte pertinente » si ≥ 2 constats hauts ou 1 haut + 2 moyens ; « amélioration ciblée préférable » si ≥ 2 moyens sans haut ; « informations insuffisantes » si la page n'a pas pu être chargée ou moins de 3 constats fiables ; sinon « aucune amélioration substantielle établie ».
