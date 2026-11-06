# Audit du site clientsici.fr

URL auditée : https://clientsici.fr/ · Domaine demandé : clientsici.fr · Domaine final : clientsici.fr · Date : 2026-11-05T21:53:21+00:00 · Outil : audit_site.py (requests + Playwright + Lighthouse 12), lecture seule, User-Agent « Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/) ».

## Synthèse

**Verdict : aucune amélioration substantielle établie** (1 haute, 1 moyenne(s), 2 basse(s)).
4 constats : 1 de gravité haute, 1 moyenne, 2 basse ; 5 page(s) consultée(s).
Lighthouse mobile (2026-11-05T21:53:31+00:00) : performance 100/100, accessibilité 100, bonnes pratiques 100, SEO 100 ; LCP 846 ms, CLS 0, TBT 0 ms.
Mobile 375 px (Playwright) : pas de débordement, 2 requêtes, 40 Ko, 1.59 s jusqu'à networkidle.
Points bloquants : Redirection http→https absente.

## Ce qui fonctionne

- En-tête HSTS présent (le navigateur force HTTPS après la première visite)
- Variante www / sans www redirigée correctement
- Balise viewport présente
- Aucun débordement horizontal à 375 px
- Aucune erreur console au chargement mobile
- Performance mobile Lighthouse 100/100 (LCP 846 ms)
- Lighthouse accessibilité 100/100
- Lighthouse SEO technique 100/100
- Lighthouse bonnes pratiques 100/100
- Titre présent (55 caractères)
- Meta description présente (151 caractères)
- H1 unique : « Votre fiche Google a un défaut qui vous coûte des appels. Je le corrig »
- Toutes les images de l'accueil ont un attribut alt (1 images)
- Ville ou zone d'intervention visible sur l'accueil (ville « Landelles » trouvée sur l'accueil)
- Données structurées LocalBusiness présentes (LocalBusiness, ProfessionalService)
- Copyright à jour (© 2026)
- Sitemap présent (https://clientsici.fr/sitemap.xml, 11 URL)
- robots.txt présent et non bloquant

## Actions prioritaires

1. **Redirection http→https absente** (haute) : Ajouter une redirection 301 de http:// vers https:// sur l'hébergement (fichier .htaccess ou réglage du panneau d'hébergement).
2. **Aucun numéro de téléphone cliquable (lien tel:)** (moyenne) : Transformer le numéro en lien <a href="tel:+33…"> et le placer en haut de page.
3. **Textes très petits sur mobile** (basse) : Utiliser une taille de texte d'au moins 14 à 16 px pour le contenu et 12 px minimum pour les mentions secondaires.
4. **Aucune mention « devis » sur l'accueil** (basse) : Ajouter un bouton « Demander un devis » visible.

## Constats détaillés

| Priorité | Problème | Preuve | Conséquence possible | Correction |
|---|---|---|---|---|
| haute | Redirection http→https absente (fait observé) | http://clientsici.fr/ — réponse 200 servie en http sans redirection (URL finale http://clientsici.fr/) | Un visiteur qui tape l'adresse sans « https » ou suit un vieux lien peut rester sur la version non sécurisée, avec l'avertissement du navigateur et un contenu dupliqué pour Google. | Ajouter une redirection 301 de http:// vers https:// sur l'hébergement (fichier .htaccess ou réglage du panneau d'hébergement). |
| moyenne | Aucun numéro de téléphone cliquable (lien tel:) (fait observé) | https://clientsici.fr/ — numéro affiché en texte : 07 56 97 45 75 ; aucun bouton de contact visible sans défiler à 375 px | Sur téléphone, le visiteur doit recopier le numéro ; une partie risque d'abandonner. | Transformer le numéro en lien <a href="tel:+33…"> et le placer en haut de page. |
| basse | Textes très petits sur mobile (mesure) | https://clientsici.fr/ — plus petit texte 11.48 px (ex. « Éditeur du site et contact »), 5 éléments sous 12 px à 375 px | Ces textes peuvent être difficiles à lire sans zoomer, en particulier les coordonnées et les mentions pratiques. | Utiliser une taille de texte d'au moins 14 à 16 px pour le contenu et 12 px minimum pour les mentions secondaires. |
| basse | Aucune mention « devis » sur l'accueil (fait observé) | https://clientsici.fr/ — mot « devis » absent du texte de l'accueil | Le visiteur peut ne pas voir comment demander un chiffrage. | Ajouter un bouton « Demander un devis » visible. |

## Mesures et conditions

- HTTP (requests, 2026-11-05T21:53:21+00:00) : URL demandée https://clientsici.fr/ → finale https://clientsici.fr/ ; chaîne : aucune redirection ; HSTS : max-age=31536000; includeSubDomains.
- Test http:// : http://clientsici.fr/ → http://clientsici.fr/ (status 200).
- Test variante www : https://www.clientsici.fr/ → https://clientsici.fr/ (status 200).
- robots.txt : présent (status 200).
- sitemap : https://clientsici.fr/sitemap.xml (urlset, 11 URL ; sans exploration exhaustive).
- Navigateur mobile 375x812 (Playwright Chromium, 2026-11-05T21:53:25+00:00) : status 200, 1.59 s jusqu'à networkidle, 2 requêtes, 40 Ko, 0 erreur(s) console, largeur défilable 375 px, plus petit texte 11.48 px.
  Captures : captures/mobile-375-fold.png, captures/mobile-375-full.png.
- Navigateur desktop 1440x900 (Playwright Chromium, 2026-11-05T21:53:25+00:00) : status 200, 0.99 s jusqu'à networkidle, 2 requêtes, 40 Ko, 0 erreur(s) console, largeur défilable 1440 px, plus petit texte 11.48 px.
  Captures : captures/desktop-1440-fold.png, captures/desktop-1440-full.png.
- Lighthouse : Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T21:53:31+00:00, URL https://clientsici.fr/ ; mesure unique depuis un serveur (pas un téléphone réel), réseau et CPU simulés ; les valeurs varient d'une mesure à l'autre ; rapport : lighthouse.json.

## Pages consultées

| Rôle | URL | Status | Title (longueur) | Description (longueur) | H1 | tel: | Images sans alt |
|---|---|---|---|---|---|---|---|
| accueil | https://clientsici.fr/ | 200 | Fiche Google artisan corrigée en 48 h, 49 € payés après (55) | 151 | 1 | 0 | 0/1 |
| services | https://clientsici.fr/site-vitrine-artisan/ | 200 | Site vitrine artisan clé en main à 79 €/mois / Clients Ici (58) | 153 | 1 | 0 | 0/1 |
| navigation | https://clientsici.fr/blog/ | 200 | Blog fiche Google artisan, SEO local et IA / Clients Ici (56) | 153 | 1 | 0 | 0/1 |
| navigation | https://clientsici.fr/fiche-google-artisan/ | 200 | Fiche Google artisan en 48 h : 49 € payés après livraison (57) | 155 | 1 | 0 | 0/1 |
| navigation | https://clientsici.fr/veille/ | 200 | Veille Reprises de Commerces & Baux B2B / Clients Ici (53) | 210 | 1 | 0 | 0/1 |

## Risques de refonte et éléments à préserver

Inventaire limité aux 5 page(s) consultée(s) ; le site peut en compter davantage (sitemap : 11). Toute page non listée ici doit être inventoriée avant mise en ligne, et chaque ancienne adresse redirigée (301).

- Pages trouvées : accueil → https://clientsici.fr/ (200); services → https://clientsici.fr/site-vitrine-artisan/ (200); navigation → https://clientsici.fr/blog/ (200); navigation → https://clientsici.fr/fiche-google-artisan/ (200); navigation → https://clientsici.fr/veille/ (200)
- Menu : Clients Ici, Fiche Google 49 €, Site vitrine 79 €/mois, le formulaire, Mentions légales complètes, Accueil, Fiche Google (49 €), Site vitrine artisan (79 €/mois), Veille B2B, Blog, Mentions légales, CGV, Confidentialité, llms.txt
- Coordonnées relevées : téléphones 07 56 97 45 75 ; e-mails contact@clientsici.fr, guillaume@clientsici.fr ; adresses 6 rue du Parc, 28190 Landelles; 44800 Saint-Herblain.
- Services listés (listes de prestations et titres H2/H3, à vérifier) : Site Vitrine Artisan Clé en Main, À lire, Fiche Google corrigée en 48 h, Je corrige en 48 h, Vous vérifiez, puis payez 49 €, Qui est derrière Clients Ici, Questions fréquentes
- Correspondance avec le lead : retrouvés : nom (« Clients Ici », https://clientsici.fr/) ; ville (« Landelles », https://clientsici.fr/) ; cp (« 28190 », https://clientsici.fr/) ; non retrouvés : siren (« 000000000 »).
- Technologie détectée : non identifiée.
- Risques : perte de pages non inventoriées, de l'historique Google si les redirections manquent, de formulaires ou d'espaces clients non visibles dans cet audit ; coordonnées à vérifier avec la fiche Google avant reprise.

## Verdict motivé

**aucune amélioration substantielle établie** : 1 haute, 1 moyenne(s), 2 basse(s). Règle : « refonte pertinente » si ≥ 2 constats hauts ou 1 haut + 2 moyens ; « amélioration ciblée préférable » si ≥ 2 moyens sans haut ; « informations insuffisantes » si la page n'a pas pu être chargée ou moins de 3 constats fiables ; sinon « aucune amélioration substantielle établie ».
