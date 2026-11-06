# Page /refonte-site-vitrine/ — notes de livraison

Fichier : `refonte-site-vitrine/index.html` (30 Ko, une seule ressource, aucun script externe, aucun cookie). Construit le 2026-11-05 à partir du gabarit réel de `/site-vitrine-artisan/` (bloc `<style>` copié tel quel, en-tête, fil d'Ariane, cartes, tableau, FAQ en `<details>`, pied de page avec vos coordonnées obfusquées, nœud JSON-LD Organisation identique) et du formulaire de l'accueil (mêmes classes `.form`, même pot de miel `site_web`, même appel à `/crm/api.php?action=public_contact`).

## Ce que contient la page

- Menu : les quatre entrées actuelles plus « Refonte » marquée active. Les autres pages du site n'ont pas encore ce lien : à ajouter sur chacune pour que la page hérite du maillage interne.
- Hero : badge « Artisans · Commerçants · Services de proximité · 100 % par écrit », H1, bouton principal vers le formulaire `#audit`, bouton secondaire `mailto:` avec l'objet « Refonte site vitrine ».
- Encart « Vous avez reçu un e-mail de ma part ? » : origine des coordonnées, réponse « STOP », statut de la maquette non sollicitée.
- « Comment ça marche » en trois étapes, tableau « Ce qui est repris, ce qui change », carte tarif collante 79 €/mois avec la clause de sortie, renvois vers la création de site et la fiche Google, FAQ de six questions reprise dans le JSON-LD FAQPage, formulaire à quatre champs (entreprise, adresse du site actuel, e-mail, activité).
- Robots `index, follow`, canonical vers `https://clientsici.fr/refonte-site-vitrine/`. La page est différenciée de l'offre création (audit du site existant, reprise du domaine, redirections, clause de sortie), ce qui justifie l'indexation. Si vous préférez une page de campagne non indexée, remplacez la balise robots par `noindex, follow` et supprimez le nœud `Service` du JSON-LD.

## Engagements écrits dans la page, à confirmer avant mise en ligne

Ces phrases sont des promesses. Elles reprennent celles de votre site quand elles existent ; les nouvelles sont marquées.

| Engagement | Origine | Statut |
|---|---|---|
| Audit par écrit sous 24 h | Reprend « réponse par e-mail sous 24 h » du diagnostic fiche Google | À confirmer pour un audit de site |
| Maquette sous 48 à 72 heures ouvrées | Reprend la FAQ de /site-vitrine-artisan/ | Cohérent |
| 79 €/mois, 0 € de frais de création, résiliable à tout moment, fin du mois en cours | Reprend l'offre et les CGV art. 9 | Cohérent |
| Nom de domaine conservé à votre nom, jamais transféré au mien | **Nouveau** | À inscrire dans les CGV |
| Copie du site (HTML et images) remise si le client arrête | **Nouveau** | À inscrire dans les CGV (l'art. 11 parle de propriété « après paiement complet », inadapté à un abonnement) |
| Maquette non sollicitée privée, hors moteurs, supprimée sur demande | **Nouveau** | À inscrire dans les CGV et la politique de confidentialité ; à appliquer techniquement (jeton non devinable, en-tête `X-Robots-Tag: noindex`) |
| Réponse « STOP » = retrait de la liste | Reprend la politique de confidentialité, point 4 | Cohérent |
| Hébergement OVH France, HTTPS, mises à jour sous 24 à 48 h incluses | Reprend /site-vitrine-artisan/ | Cohérent |

## Avant publication

1. Déposer `index.html` dans `/refonte-site-vitrine/` à la racine du site (le serveur sert déjà des dossiers avec `index.html`, comme pour les autres pages).
2. Vérifier que `/crm/api.php?action=public_contact` accepte et enregistre les champs supplémentaires `site_actuel`, `secteur` et `source: "refonte"`. En local, la requête part correctement ; le CRM n'a pas pu être testé. Si le CRM ignore les champs inconnus, l'envoi fonctionnera mais vous perdrez l'adresse du site : ajoutez-les côté serveur.
3. CGV : ajouter la refonte à l'article 3, un article sur la clause de sortie et un sur le statut des maquettes non commandées ; changer la date de version. Politique de confidentialité : une ligne sur les maquettes.
4. Ajouter le lien « Refonte » au menu et au pied de page des autres pages, l'URL au `sitemap.xml` (avec `lastmod` réel), une entrée dans `llms.txt` et `llms-full.txt`, et une carte « Vous avez déjà un site ? » sur l'accueil dans la section « Besoin d'un site en plus de la fiche ? ».
5. Faire pointer tous les e-mails de prospection vers `https://clientsici.fr/refonte-site-vitrine/`, jamais vers l'accueil.
6. Après mise en ligne, relancer une mesure PageSpeed Insights hors quota avant toute affirmation chiffrée de vitesse.

## Tests réalisés

Voir `captures-tests/rapport-tests.md` et les captures `refonte-{375,768,1440}-{fold,full,tarif,form}.png`. Résumé : aucun débordement, aucune erreur JavaScript, aucune ressource manquante, validation locale du formulaire (vide, URL invalide), envoi vers le CRM confirmé avec message d'échec honnête quand le serveur ne répond pas, parcours clavier jusqu'au bouton en 24 tabulations, libellés présents sur les quatre champs, menu actif, robots et canonical corrects, Lighthouse local 100/100/100/100. Non testé : appareils physiques, réception réelle par le CRM.

## Choix de texte

Voix conservée : « je », phrases courtes, aucune promesse de classement (répétée dans la FAQ), tarif et TVA mentionnés comme sur le reste du site. Aucun chiffre inventé : la seule affirmation technique (« une seule page HTML légère, sans script extérieur ni cookie ») est vérifiable sur la page elle-même. Pas de témoignage ni de réalisation, faute de matière : à ajouter dès les premiers clients avec accord écrit (CGV art. 12).
