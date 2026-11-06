# Audit du site www.service-public.gouv.fr

URL auditée : https://www.service-public.gouv.fr/ · Date : 2026-11-05T20:53:34+00:00 · Outil : audit_site.py (requests + Playwright + Lighthouse 12), lecture seule, User-Agent « Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/) ».

## Synthèse

**Verdict : amélioration ciblée préférable** (2 constats moyens, aucun haut).
6 constats : 0 de gravité haute, 2 moyenne, 4 basse ; 2 page(s) consultée(s).
Lighthouse mobile (2026-11-05T20:54:03+00:00) : performance 67/100, accessibilité 100, bonnes pratiques 96, SEO 100 ; LCP 6379 ms, CLS 0.075, TBT 185 ms.
Mobile 375 px (Playwright) : pas de débordement, 93 requêtes, 888 Ko, 4.93 s jusqu'à networkidle.

## Ce qui fonctionne

- En-tête HSTS présent (le navigateur force HTTPS après la première visite)
- Variante www / sans www redirigée correctement
- Balise viewport présente
- Aucun débordement horizontal à 375 px
- Lighthouse accessibilité 100/100
- Lighthouse SEO technique 100/100
- Lighthouse bonnes pratiques 96/100
- Titre présent (24 caractères)
- Meta description présente (56 caractères)
- H1 unique : « Bienvenue sur le site officiel d’information et de démarches administr »
- Ville ou zone d'intervention visible sur l'accueil (adresse détectée : 89100 Sens)
- Sitemap présent (https://www.service-public.gouv.fr/sitemap.xml, 14 sous-sitemaps URL)
- robots.txt présent et non bloquant

## Actions prioritaires

1. **Performance mobile moyenne (Lighthouse)** (moyenne) : Optimiser images et scripts ; viser un LCP sous 2,5 s.
2. **Aucun numéro de téléphone cliquable (lien tel:)** (moyenne) : Transformer le numéro en lien <a href="tel:+33…"> et le placer en haut de page.
3. **Erreurs JavaScript ou ressources en échec au chargement** (basse) : Corriger ou retirer les scripts en erreur ; vérifier les fichiers manquants (404).
4. **Images sans attribut alt** (basse) : Décrire chaque photo en une phrase (ex. « Pose de carrelage, cuisine à Chartres »).
5. **Données structurées LocalBusiness absentes** (basse) : Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google.
6. **Aucune mention « devis » sur l'accueil** (basse) : Ajouter un bouton « Demander un devis » visible.

## Constats détaillés

| Priorité | Problème | Preuve | Conséquence possible | Correction |
|---|---|---|---|---|
| moyenne | Performance mobile moyenne (Lighthouse) (mesure) | https://www.service-public.gouv.fr/ — performance 67/100, LCP 6379 ms, CLS 0.075, TBT 185 ms (Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T20:54:03+00:00) | Affichage perceptiblement lent sur réseau mobile ordinaire. | Optimiser images et scripts ; viser un LCP sous 2,5 s. |
| moyenne | Aucun numéro de téléphone cliquable (lien tel:) (fait observé) | https://www.service-public.gouv.fr/ — aucun lien tel: ni numéro détecté sur les pages consultées | Sur téléphone, le visiteur doit recopier le numéro ; une partie abandonne. | Transformer le numéro en lien <a href="tel:+33…"> et le placer en haut de page. |
| basse | Erreurs JavaScript ou ressources en échec au chargement (mesure) | https://www.service-public.gouv.fr/ — 1 erreur(s) console à 375 px, ex. : JS: Failed to execute 'replaceChild' on 'Node': The node to be replaced is not a child of this node. | Des fonctions (menu, formulaire, carrousel) peuvent ne pas marcher chez certains visiteurs. | Corriger ou retirer les scripts en erreur ; vérifier les fichiers manquants (404). |
| basse | Images sans attribut alt (fait observé) | https://www.service-public.gouv.fr/ — 20 image(s) sans alt sur 2 page(s) consultée(s) (accueil : 10/16) | Photos de chantiers invisibles pour Google Images et les lecteurs d'écran. | Décrire chaque photo en une phrase (ex. « Pose de carrelage, cuisine à Chartres »). |
| basse | Données structurées LocalBusiness absentes (fait observé) | https://www.service-public.gouv.fr/ — types JSON-LD trouvés : aucun | Google doit deviner nom, adresse, téléphone et horaires au lieu de les lire. | Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google. |
| basse | Aucune mention « devis » sur l'accueil (fait observé) | https://www.service-public.gouv.fr/ — mot « devis » absent du texte de l'accueil | Le visiteur ne voit pas comment demander un chiffrage. | Ajouter un bouton « Demander un devis » visible. |

Non vérifié / non mesuré : redirection http→https non vérifiée (délai dépassé (12 s)).

## Mesures et conditions

- HTTP (requests, 2026-11-05T20:53:34+00:00) : URL demandée https://www.service-public.fr/ → finale https://www.service-public.gouv.fr/ ; chaîne : 301 https://www.service-public.fr/ ; HSTS : max-age=63072000; includeSubDomains; preload.
- Test http:// : http://www.service-public.gouv.fr/ → aucune réponse (status None, erreur : délai dépassé (12 s)).
- Test variante www : https://service-public.gouv.fr/ → https://www.service-public.gouv.fr/ (status 200).
- robots.txt : présent (status 200).
- sitemap : https://www.service-public.gouv.fr/sitemap.xml (index, 14 sous-sitemaps URL ; sans exploration exhaustive).
- Navigateur mobile 375x812 (Playwright Chromium, 2026-11-05T20:53:50+00:00) : status 200, 4.93 s jusqu'à networkidle, 93 requêtes, 888 Ko, 1 erreur(s) console, largeur défilable 375 px, plus petit texte 6.4 px.
  Captures : captures/mobile-375-fold.png, captures/mobile-375-full.png.
- Navigateur desktop 1440x900 (Playwright Chromium, 2026-11-05T20:53:50+00:00) : status 200, 4.63 s jusqu'à networkidle, 100 requêtes, 953 Ko, 2 erreur(s) console, largeur défilable 1440 px, plus petit texte 12 px.
  Captures : captures/desktop-1440-fold.png, captures/desktop-1440-full.png.
- Lighthouse : Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T20:54:03+00:00, URL https://www.service-public.gouv.fr/ ; mesure unique depuis un serveur (pas un téléphone réel), réseau et CPU simulés ; les valeurs varient d'une mesure à l'autre ; rapport : lighthouse.json.

## Pages consultées

| Rôle | URL | Status | Title (longueur) | Description (longueur) | H1 | tel: | Images sans alt |
|---|---|---|---|---|---|---|---|
| accueil | https://www.service-public.gouv.fr/ | 200 | Accueil / Service Public (24) | 56 | 1 | 0 | 10/16 |
| contact | https://www.service-public.gouv.fr/contact/accueil | 200 | Contact / Service Public (24) | 56 | 1 | 0 | 10/15 |

## Risques de refonte et éléments à préserver

Inventaire limité aux 2 page(s) consultée(s) ; le site peut en compter davantage (sitemap : nombre inconnu). Toute page non listée ici doit être inventoriée avant mise en ligne, et chaque ancienne adresse redirigée (301).

- Pages trouvées : accueil → https://www.service-public.gouv.fr/ (200); contact → https://www.service-public.gouv.fr/contact/accueil (200)
- Menu : Se connecter, Accueil, Actualité de vos droits et démarches, Je déménage, Je cherche un emploi, Je deviens parent, Je veux obtenir un crédit immobilier, J'achète un logement, Je prépare ma retraite, Un proche est décédé, Voir tous les événements de vie, Papiers - Citoyenneté - Élections, Famille - Scolarité, Social - Santé, Travail - Formation
- Coordonnées relevées : téléphones aucun ; e-mails aucun ; adresses 32 rue Olympe de Gouges, 89100 Sens.
- Services listés (titres H2/H3, à vérifier) : Fiches pratiques par événement de vie, France Services, Fiches pratiques les plus lues, Démarches et outils, Actualité de vos droits et démarches, Recevoir la lettre de Service Public, Je déménage, Je deviens parent, Je recherche un emploi, Je prépare ma retraite, Besoin d’aide près de chez vous ?, Calendrier des vacances scolaires 2026-2027 et 2027-2028, Renouvellement du passeport d'un majeur, Durée de conservation des papiers, Aides pour financer le permis de conduire
- Technologie détectée : non identifiée.
- Risques : perte de pages non inventoriées, de l'historique Google si les redirections manquent, de formulaires ou d'espaces clients non visibles dans cet audit ; coordonnées à vérifier avec la fiche Google avant reprise.

## Verdict motivé

**amélioration ciblée préférable** : 2 constats moyens, aucun haut. Règle : « refonte pertinente » si ≥ 2 constats hauts ou 1 haut + 2 moyens ; « amélioration ciblée préférable » si ≥ 2 moyens sans haut ; « informations insuffisantes » si la page n'a pas pu être chargée ou moins de 3 constats fiables ; sinon « aucune amélioration substantielle établie ».

Limites : redirection http→https non vérifiée (délai dépassé (12 s)). Les détections de ville, d'adresse et de services sont heuristiques et doivent être relues.
