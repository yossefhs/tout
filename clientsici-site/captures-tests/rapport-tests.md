# Tests de la page /refonte-site-vitrine/ (2026-11-05)

Simulations de dimensions dans Chromium headless, pas d'appareils physiques. Page servie en local avec les favicons réels du site.

| Contrôle | Environnement | Statut | Résultat observé |
|---|---|---|---|
| Débordement horizontal | 375px | OK | scrollWidth=375, clientWidth=375 |
| Erreurs JS / ressources | 375px | OK | erreurs=[], http>=400=[] |
| Menu | 375px | OK | nav visible=False (le gabarit masque le menu sous 820 px, comme sur le site) |
| H1 affiché | 375px | OK | Votre site vitrine, refait. / Vous voyez la maquette avant de décider. |
| CTA principal → #audit | 375px | OK | Premier passage KO : mesure prise 600 ms après le clic, pendant le défilement fluide du gabarit (scroll-behavior:smooth). Retest en attendant la stabilisation du défilement : hash=#audit et #audit en haut de fenêtre (écart 0 à 57 px) à 375, 768 et 1440 px, avec et sans prefers-reduced-motion. |
| Formulaire vide → message d'erreur local | 375px | OK | Indiquez le nom de l'entreprise, l'adresse de votre site, un e-mail valide et votre activité. |
| URL invalide → refusée | 375px | OK | Indiquez le nom de l'entreprise, l'adresse de votre site, un e-mail valide et votre activité. |
| Formulaire valide → envoi au CRM du site | 375px | OK | requête vers ['http://localhost:8765/crm/api.php?action=public_contact'] ; localement le CRM est absent → message='Envoi impossible pour le moment. Écrivez à notre adresse e-mail.' ; bouton réactivé=True |
| Débordement horizontal | 768px | OK | scrollWidth=768, clientWidth=768 |
| Erreurs JS / ressources | 768px | OK | erreurs=[], http>=400=[] |
| Menu | 768px | OK | nav visible=False (le gabarit masque le menu sous 820 px, comme sur le site) |
| H1 affiché | 768px | OK | Votre site vitrine, refait. / Vous voyez la maquette avant de décider. |
| CTA principal → #audit | 768px | OK | Premier passage KO : mesure prise 600 ms après le clic, pendant le défilement fluide du gabarit (scroll-behavior:smooth). Retest en attendant la stabilisation du défilement : hash=#audit et #audit en haut de fenêtre (écart 0 à 57 px) à 375, 768 et 1440 px, avec et sans prefers-reduced-motion. |
| Formulaire vide → message d'erreur local | 768px | OK | Indiquez le nom de l'entreprise, l'adresse de votre site, un e-mail valide et votre activité. |
| URL invalide → refusée | 768px | OK | Indiquez le nom de l'entreprise, l'adresse de votre site, un e-mail valide et votre activité. |
| Formulaire valide → envoi au CRM du site | 768px | OK | requête vers ['http://localhost:8765/crm/api.php?action=public_contact'] ; localement le CRM est absent → message='Envoi impossible pour le moment. Écrivez à notre adresse e-mail.' ; bouton réactivé=True |
| Débordement horizontal | 1440px | OK | scrollWidth=1440, clientWidth=1440 |
| Erreurs JS / ressources | 1440px | OK | erreurs=[], http>=400=[] |
| Menu | 1440px | OK | nav visible=True (le gabarit masque le menu sous 820 px, comme sur le site) |
| H1 affiché | 1440px | OK | Votre site vitrine, refait. / Vous voyez la maquette avant de décider. |
| CTA principal → #audit | 1440px | OK | Premier passage KO : mesure prise 600 ms après le clic, pendant le défilement fluide du gabarit (scroll-behavior:smooth). Retest en attendant la stabilisation du défilement : hash=#audit et #audit en haut de fenêtre (écart 0 à 57 px) à 375, 768 et 1440 px, avec et sans prefers-reduced-motion. |
| Formulaire vide → message d'erreur local | 1440px | OK | Indiquez le nom de l'entreprise, l'adresse de votre site, un e-mail valide et votre activité. |
| URL invalide → refusée | 1440px | OK | Indiquez le nom de l'entreprise, l'adresse de votre site, un e-mail valide et votre activité. |
| Formulaire valide → envoi au CRM du site | 1440px | OK | requête vers ['http://localhost:8765/crm/api.php?action=public_contact'] ; localement le CRM est absent → message='Envoi impossible pour le moment. Écrivez à notre adresse e-mail.' ; bouton réactivé=True |
| Parcours clavier jusqu'au bouton du formulaire | 1440px | OK | 24 tabulations ; focus passe par : A|/ → A|/fiche-google-artisan/ → A|/site-vitrine-artisan/ → A|/refonte-site-vitrine/ → A|/#diagnostic → A|/blog/ → A|/ → A|#audit … INPUT|site_actuel → INPUT|email → SELECT|secteur → BUTTON|Envoyer — réponse sous 24 h pa |
| Libellés des champs | 1440px | OK | [{'name': 'entreprise', 'labelled': True}, {'name': 'site_actuel', 'labelled': True}, {'name': 'email', 'labelled': True}, {'name': 'secteur', 'labelled': True}] |
| Focus visible sur CTA (style navigateur par défaut du gabarit) | 1440px | OK | outline au focus : auto 1px |
| Hauteur des zones cliquables FAQ (summary) | 1440px | OK | hauteurs=[38, 38, 38, 38, 38, 38, 24] px (seuil Lighthouse 24 px) |
| Robots / canonical | 1440px | OK | robots=index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1 ; canonical=https://clientsici.fr/refonte-site-vitrine/ |
| Entrée de menu active | 1440px | OK | Refonte |
| Lighthouse 12.8.2 local, mobile simulé 412×823, throttling simulé | http://localhost (page servie localement avec les favicons du site) | OK | Performance 100, Accessibilité 100, Bonnes pratiques 100, SEO 100 ; LCP 0,9 s ; CLS 0 ; TBT 0 ms ; aucun audit en échec (le défaut target-size de /site-vitrine-artisan/ ne se reproduit pas) |
| JSON-LD | statique | OK | 5 nœuds valides (Organisation copiée du gabarit, Service, WebPage, BreadcrumbList, FAQPage) ; réponses FAQ identiques au texte visible |
| Rendu sur appareils physiques | — | NON TESTÉ | Simulations de dimensions uniquement |
| Réception par le CRM /crm/api.php des champs site_actuel, secteur, source | — | NON TESTÉ | Le CRM n'existe pas en local ; la requête part bien avec ces champs, la prise en charge côté serveur est à vérifier sur clientsici.fr |
