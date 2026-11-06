# Audit du site example.com

URL auditée : http://example.com/ · Date : 2026-11-05T20:53:18+00:00 · Outil : audit_site.py (requests + Playwright + Lighthouse 12), lecture seule, User-Agent « Mozilla/5.0 (compatible; ClientsIci-audit; +https://clientsici.fr/) ».

## Synthèse

**Verdict : refonte pertinente** (1 constat(s) de gravité haute et 3 moyenne(s)).
7 constats : 1 de gravité haute, 3 moyenne, 3 basse ; 1 page(s) consultée(s).
Lighthouse mobile (2026-11-05T20:53:22+00:00) : performance 100/100, accessibilité 100, bonnes pratiques 83, SEO 80 ; LCP 1117 ms, CLS 0, TBT 0 ms.
Mobile 375 px (Playwright) : pas de débordement, 2 requêtes, 2 Ko, 0.62 s jusqu'à networkidle.
Points bloquants : Redirection http→https absente (HTTPS disponible mais non forcé).

## Ce qui fonctionne

- Balise viewport présente
- Aucun débordement horizontal à 375 px
- Aucune erreur console au chargement mobile
- Performance mobile Lighthouse 100/100 (LCP 1117 ms)
- Lighthouse accessibilité 100/100
- Titre présent (14 caractères)

## Actions prioritaires

1. **Redirection http→https absente (HTTPS disponible mais non forcé)** (haute) : Rediriger (301) tout le trafic http:// vers https:// et déclarer la version https dans la Search Console.
2. **Meta description absente sur l'accueil** (moyenne) : Rédiger une description de 120 à 155 caractères avec métier, zone et appel à l'action.
3. **Aucun numéro de téléphone cliquable (lien tel:)** (moyenne) : Transformer le numéro en lien <a href="tel:+33…"> et le placer en haut de page.
4. **Aucune ville ni zone d'intervention repérée sur l'accueil** (moyenne) : Écrire la ville et le rayon d'intervention dans le titre, le H1 et le pied de page.
5. **Aucun titre H1 sur l'accueil** (basse) : Ajouter un H1 unique en haut de page : métier, ville, promesse.
6. **Données structurées LocalBusiness absentes** (basse) : Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google.
7. **Aucune mention « devis » sur l'accueil** (basse) : Ajouter un bouton « Demander un devis » visible.

## Constats détaillés

| Priorité | Problème | Preuve | Conséquence possible | Correction |
|---|---|---|---|---|
| haute | Redirection http→https absente (HTTPS disponible mais non forcé) (fait observé) | http://example.com/ — URL finale en http (réponse 200) alors que https://example.com/ répond 200 | Le visiteur qui arrive sans « https » voit « Non sécurisé » ; deux versions du site coexistent pour Google. | Rediriger (301) tout le trafic http:// vers https:// et déclarer la version https dans la Search Console. |
| moyenne | Meta description absente sur l'accueil (fait observé) | http://example.com/ — aucune <meta name="description"> | Google compose lui-même l'extrait ; il manque l'accroche (zone, devis gratuit, urgence). | Rédiger une description de 120 à 155 caractères avec métier, zone et appel à l'action. |
| moyenne | Aucun numéro de téléphone cliquable (lien tel:) (fait observé) | http://example.com/ — aucun lien tel: ni numéro détecté sur les pages consultées | Sur téléphone, le visiteur doit recopier le numéro ; une partie abandonne. | Transformer le numéro en lien <a href="tel:+33…"> et le placer en haut de page. |
| moyenne | Aucune ville ni zone d'intervention repérée sur l'accueil (fait observé) | http://example.com/ — aucun code postal + ville, département ou formule de zone détecté (heuristique ; à confirmer à l'œil) | Le visiteur ne sait pas si l'entreprise intervient chez lui ; Google ne relie pas le site à la zone. | Écrire la ville et le rayon d'intervention dans le titre, le H1 et le pied de page. |
| basse | Aucun titre H1 sur l'accueil (fait observé) | http://example.com/ — 0 balise <h1> | Le message principal (métier + ville) n'est pas identifié comme titre par les moteurs et les lecteurs d'écran. | Ajouter un H1 unique en haut de page : métier, ville, promesse. |
| basse | Données structurées LocalBusiness absentes (fait observé) | http://example.com/ — types JSON-LD trouvés : aucun | Google doit deviner nom, adresse, téléphone et horaires au lieu de les lire. | Ajouter un bloc JSON-LD LocalBusiness (nom, adresse, téléphone, horaires, zone) cohérent avec la fiche Google. |
| basse | Aucune mention « devis » sur l'accueil (fait observé) | http://example.com/ — mot « devis » absent du texte de l'accueil | Le visiteur ne voit pas comment demander un chiffrage. | Ajouter un bouton « Demander un devis » visible. |

## Mesures et conditions

- HTTP (requests, 2026-11-05T20:53:18+00:00) : URL demandée http://example.com/ → finale http://example.com/ ; chaîne : aucune redirection ; HSTS : absent.
- Test https:// : https://example.com/ → https://example.com/ (status 200).
- Test variante www : http://www.example.com/ → http://www.example.com/ (status 200).
- robots.txt : absent ou non lisible (status 404).
- sitemap : aucun trouvé parmi http://example.com/sitemap.xml, http://example.com/sitemap_index.xml.
- Navigateur mobile 375x812 (Playwright Chromium, 2026-11-05T20:53:18+00:00) : status 200, 0.62 s jusqu'à networkidle, 2 requêtes, 2 Ko, 0 erreur(s) console, largeur défilable 375 px, plus petit texte 14 px.
  Captures : captures/mobile-375-fold.png, captures/mobile-375-full.png.
- Navigateur desktop 1440x900 (Playwright Chromium, 2026-11-05T20:53:18+00:00) : status 200, 0.62 s jusqu'à networkidle, 2 requêtes, 2 Ko, 0 erreur(s) console, largeur défilable 1440 px, plus petit texte 14 px.
  Captures : captures/desktop-1440-fold.png, captures/desktop-1440-full.png.
- Lighthouse : Lighthouse 12 (npx lighthouse@12), émulation mobile, throttling simulé, 2026-11-05T20:53:22+00:00, URL https://example.com/ ; mesure unique depuis un serveur (pas un téléphone réel), réseau et CPU simulés ; les valeurs varient d'une mesure à l'autre ; rapport : lighthouse.json.

## Pages consultées

| Rôle | URL | Status | Title (longueur) | Description (longueur) | H1 | tel: | Images sans alt |
|---|---|---|---|---|---|---|---|
| accueil | http://example.com/ | 200 | Example Domain (14) | 0 | 0 | 0 | 0/0 |

## Risques de refonte et éléments à préserver

Inventaire limité aux 1 page(s) consultée(s) ; le site peut en compter davantage (sitemap : nombre inconnu). Toute page non listée ici doit être inventoriée avant mise en ligne, et chaque ancienne adresse redirigée (301).

- Pages trouvées : accueil → http://example.com/ (200)
- Menu : aucun lien de navigation repéré
- Coordonnées relevées : téléphones aucun ; e-mails aucun ; adresses aucune détectée.
- Services listés (titres H2/H3, à vérifier) : aucun relevé
- Technologie détectée : non identifiée.
- Risques : perte de pages non inventoriées, de l'historique Google si les redirections manquent, de formulaires ou d'espaces clients non visibles dans cet audit ; coordonnées à vérifier avec la fiche Google avant reprise.

## Verdict motivé

**refonte pertinente** : 1 constat(s) de gravité haute et 3 moyenne(s). Règle : « refonte pertinente » si ≥ 2 constats hauts ou 1 haut + 2 moyens ; « amélioration ciblée préférable » si ≥ 2 moyens sans haut ; « informations insuffisantes » si la page n'a pas pu être chargée ou moins de 3 constats fiables ; sinon « aucune amélioration substantielle établie ».
