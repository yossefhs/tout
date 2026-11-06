# Offre de refonte : sur clientsici.fr ou sur un site dédié ?

Date : 2026-11-05. Matériel : 8 pages de clientsici.fr téléchargées (accueil, site-vitrine-artisan, fiche-google-artisan, veille, blog, mentions légales, CGV, confidentialité), robots.txt, sitemap.xml, llms.txt, captures mobile 375×812 et ordinateur 1440×900, Lighthouse 12.8.2 local, vérifications HTTP. Méthode : quatre analyses indépendantes (positionnement, regard du prospect, SEO/technique, faisabilité opérationnelle et juridique), une synthèse, puis une contre-expertise chargée de la réfuter. Les faits ci-dessous ont été revérifiés après la contre-expertise. Aucun concurrent analysé, aucune donnée privée.

## 1. Verdict

**Même site, par une page d'atterrissage dédiée, à deux conditions.** Les quatre angles et la contre-expertise convergent : la refonte s'emboîte dans la ligne existante « Site vitrine artisan 79 €/mois » et le site porte déjà le socle de confiance qu'un dirigeant vérifie avant de répondre à un e-mail. Un site dédié repartirait de zéro sur tout cela.

Les deux conditions :

1. **La cible de la refonte reste « artisans et commerces locaux ».** Si vous visez toutes les TPE (professions libérales, services, e-commerce), le mot « artisan » est inscrit dans la marque elle-même (titles des mentions légales et des CGV, llms.txt, jobTitle du fondateur, blog, badges) : la réponse n'est alors pas une page, mais une réécriture transversale des 8 pages, ou un site dédié. À chiffrer avant de trancher.
2. **La refonte est vendue comme l'offre existante : 79 €/mois sans engagement, 0 € de frais de création, maquette avant engagement.** Un forfait ou un devis avec acompte contredirait en un clic le tableau comparatif de /site-vitrine-artisan/ (« 0 € de frais de création » contre « 1 500 € à 3 500 € HT d'acompte » chez les agences) et la FAQ « aucun frais de mise en service caché ». Dans ce cas : réécrire ce comparatif d'abord, ou site dédié.

**Critère de bascule à poser dès le départ** : ajoutez un champ « secteur d'activité » au formulaire de la page refonte. Si, après un volume d'e-mails que vous fixez, plus de la moitié des réponses viennent de TPE non artisanes, ou si la question « c'est la même chose que votre site artisan ? » revient, réévaluez vers un site dédié.

## 2. Pourquoi « même site »

- **La refonte est déjà promise sur ce domaine.** La FAQ de /site-vitrine-artisan/ traite « un vieux site en HTTP ou un nom de domaine » avec remplacement et redirections 301, et le bouton principal est « Demander une maquette par e-mail » : c'est exactement la mécanique maquette-avant-vente de la prospection (fait observé).
- **Le socle de confiance existe.** Pied de page avec identité complète (EI, SIRET, RCS Chartres, adresse, téléphone), mentions légales et confidentialité du 28 septembre 2026, CGV du 2 novembre 2026, Stripe et OVH nommés, « payés après », « sans engagement ». Un domaine neuf aurait, pour un prospect méfiant, le profil d'un démarcheur inconnu (hypothèse raisonnable, non testée auprès de prospects).
- **La prospection B2B est déjà couverte juridiquement.** Politique de confidentialité, point 4 : coordonnées professionnelles publiques, intérêt légitime, réponse « STOP », liste d'opposition. CGV art. 2 : « professionnels (entreprises, artisans, commerçants, professions libérales) ». Rien à recréer.
- **Le coût d'un second site est disproportionné pour une personne seule** : domaine, hébergement, certificat, trois pages légales, formulaire relié au CRM (/crm/api.php), sitemap, robots, llms.txt, JSON-LD, favicons, OG, puis entretien permanent. Nuance de la contre-expertise : les pages actuelles semblent maintenues à la main (JSON-LD, menus et pieds de page divergent d'une page à l'autre), donc la page dédiée et ses à-côtés représentent plutôt 2 à 4 jours que « quelques heures ».
- **La marque sait déjà loger une ligne distincte hors du hero** : la Veille B2B a sa page, son menu d'ancres, son article de CGV, sans toucher à l'accueil « fiche Google ». Que cela fonctionne commercialement n'est pas mesuré (hypothèse).
- **Les deux vrais arguments pour un site dédié se traitent autrement** : la réputation du domaine face aux plaintes se gère par un domaine d'envoi secondaire (voir § 4), et l'alignement e-mail → page se gère par la page d'atterrissage.

Argument écarté : « le site est lui-même la preuve technique ». Les mesures (ci-dessous) sont bonnes, mais ne discriminent pas entre les deux options.

## 3. Quand un site dédié deviendrait pertinent

- Cible élargie à toutes les TPE sans vouloir réécrire la marque « fiche Google artisan ».
- Refonte vendue au forfait ou au devis avec montant initial.
- Refus de faire pointer les e-mails vers une page dédiée : l'accueil parle exclusivement de fiche Google à 49 € pour « plombiers, chauffagistes » au-dessus de la ligne de flottaison (capture `captures-clientsici/home-mobile-fold.png`).
- La refonte dépasse la fiche Google en volume et la majorité des clients ne sont ni artisans ni commerces locaux.
- Projet de céder un jour l'activité « sites web » séparément.
- Discours de vente incompatible avec le pied de page « Aucune promesse de position Google ni de volume de clients » (déconseillé de toute façon).

## 4. Changements recommandés sur clientsici.fr, dans l'ordre

1. **Clause de sortie dans les CGV et sur la page** (avant toute prospection) : nom de domaine toujours au nom du client, export du site remis à la résiliation, aucune rétention. Les CGV art. 11 parlent de propriété « après paiement complet », notion inopérante pour un abonnement sans fin ; un prospect « refonte » possède déjà un domaine et voudra savoir ce qu'il récupère. Ajouter la refonte à l'art. 3 (qui ne liste pas non plus l'option vidéos ~49 €/mois affichée sur /fiche-google-artisan/) et un article sur le statut des maquettes non commandées (propriété de Clients Ici, privées, supprimées sur refus, éléments du prospect utilisés uniquement pour la démonstration). Changer la date de version.
2. **Page d'atterrissage /refonte-site-vitrine/** (404 aujourd'hui, vérifié) : title et H1 sans le mot « artisan », avec « votre site actuel », « audit », « maquette » ; méthode en trois étapes (je regarde votre site ; je vous envoie l'audit et une maquette ; vous décidez) ; encart « Vous avez reçu un e-mail de ma part ? » ; formulaire avec « adresse de votre site actuel » et « secteur d'activité ». **Ne pas créer une seconde page indexable pour le même produit** : soit `noindex` ou `canonical` vers /site-vitrine-artisan/ (page de campagne), soit indexable seulement si la refonte est réellement différenciée (migration du contenu, reprise du domaine, 301, audit). Tous les liens des e-mails pointent vers cette page, jamais vers l'accueil.
3. **Hébergement des maquettes de prospection** : priorité haute, pas basse. Elles contiennent le nom, parfois le logo et les textes d'un tiers qui n'a rien demandé. Sous-domaine technique ou dossier `/apercu/<jeton-non-devinable>/`, en-tête `X-Robots-Tag: noindex, nofollow`, aucun script tiers, suppression automatique après délai, mention « maquette non sollicitée, propriété de Clients Ici, supprimée sur demande » dans la maquette et dans l'e-mail. Aujourd'hui /maquette/ et /apercu/ répondent 403 et /crm/ 401 (vérifié le 2026-11-05) : la protection vient de là, pas du robots.txt, qui rend ces chemins publics. Détail dans `hebergement-maquette-clientsici.md`.
4. **Domaine d'envoi distinct du domaine du site** : un ou deux domaines secondaires visiblement liés, redirigés vers clientsici.fr, SPF/DKIM/DMARC alignés, chauffe de quelques semaines, jamais d'envoi depuis contact@ ni guillaume@clientsici.fr (cette seconde adresse apparaît sur /veille/). Arbitrage à assumer : garder les liens vers clientsici.fr dans les e-mails apporte la crédibilité, mais les filtres peuvent aussi juger la réputation des domaines liés (connaissance générale, non mesurée ici). Donc volumes faibles, e-mails individuels, URL nue sans lien de suivi, surveillance Google Postmaster sur clientsici.fr.
5. **Menu et pied de page** : entrée « Refonte » ou « Site vitrine / refonte » partout ; menu identique sur toutes les pages (« Questions » sur l'accueil, « Blog » sur la page site) ; Veille B2B maintenue hors menu principal ; ajouter sur /veille/ la mention « Aucune promesse de position Google ni de volume de clients », absente de son pied de page (vérifié).
6. **Accueil** : une carte « Vous avez déjà un site ? Audit et maquette avant tout engagement » dans la section « Besoin d'un site en plus de la fiche ? », sans toucher au H1.
7. **Preuves de compétence web** : aucune réalisation, aucun avis, aucune capture de site livré sur les 8 pages, alors que la page site vitrine affirme qu'un client vérifie « vraies photos et avis clients » en 8 secondes. Captures de maquettes anonymisées, un avant/après, puis témoignages avec accord écrit (CGV art. 12).
8. **Cohérence éditoriale** sur /site-vitrine-artisan/ : « Je crée » puis « nous connectons / nous remplaçons / Nous conservons » ; « Modifications incluses sur simple WhatsApp » puis « Vous me l'envoyez par e-mail » (vérifié). Choisir « je » et un canal.
9. **Métadonnées** : llms.txt et llms-full.txt (existe, 200), JSON-LD `hasOfferCatalog` et `priceRange` (« 49€ - 79€/mois » ignore la veille à 149 €/mois), description de l'organisation et jobTitle élargis si la cible s'élargit ; sitemap_index.xml renvoie 404 alors que seul sitemap.xml existe (sans conséquence si rien ne le référence).
10. **Détails techniques** : audit Lighthouse `target-size` sur les `<summary>` de la FAQ de /site-vitrine-artisan/ (accessibilité 93) ; regrouper les Disallow du robots.txt en un bloc ; refaire une mesure PageSpeed Insights hors quota avant toute affirmation chiffrée de vitesse dans les e-mails.

Regroupement suggéré par la contre-expertise : une seule offre « site » (création, refonte, option vidéos) ramène la marque à trois blocs lisibles : fiche Google, site, veille B2B.

## 5. Faits, mesures, hypothèses

Faits observés (fichiers dans `captures-clientsici/` et extraits texte de la session) :

- Accueil mono-produit : title « Fiche Google artisan corrigée en 48 h, 49 € payés après », H1 sur la fiche Google, badge « Plombiers, chauffagistes, artisans et commerces locaux » ; l'offre site n'apparaît qu'en bouton secondaire puis en section basse.
- Le mot « refonte » n'apparaît sur aucune des 8 pages ; /refonte-site-vitrine/ et /refonte/ répondent 404.
- Occurrences du mot « artisan » dans le texte visible : 17 (accueil), 43 (site vitrine), 46 (fiche Google).
- Cinq lignes d'offre affichées : Test IA 29 €, fiche 49 €, site 79 €/mois, option vidéos ~49 €/mois, veille 149 €/mois ou 10 % de commission.
- robots.txt : Disallow /crm/, /crm/data/, /maquette/, /apercu/ pour 8 user-agents ; HEAD le 2026-11-05 : /maquette/ 403, /apercu/ 403, /crm/ 401, /llms-full.txt 200.
- Formulaire de l'accueil posté vers /crm/api.php (CRM maison sur le domaine) ; paiement par liens Stripe externes.
- Pied de page avec identité complète sur les pages artisans ; pied de page de /veille/ sans la mention « Aucune promesse… ».
- Site récent : mentions légales et confidentialité du 28 septembre 2026, CGV du 2 novembre 2026, 3 articles de blog, sitemap de 11 URL toutes en lastmod 2026-11-04.

Mesures (laboratoire, conteneur cloud, pas d'appareil réel ni de données d'utilisateurs) :

| Page | Outil, date, conditions | Résultat |
|---|---|---|
| https://clientsici.fr/ | Lighthouse 12.8.2 local, 2026-11-05 17:51 UTC, mobile simulé 412×823, throttling simulé, Chromium headless | Performance 100, Accessibilité 100, Bonnes pratiques 100, SEO 100 ; LCP 0,9 s ; CLS 0 ; TBT 20 ms |
| https://clientsici.fr/site-vitrine-artisan/ | idem, 17:52 UTC | 100 / 93 / 100 / 100 ; LCP 0,9 s ; CLS 0 ; seul écart : `target-size` sur les `<summary>` |
| 4 pages, 375 px et 1440 px | Playwright Node, Chromium 153, 2026-11-05 | 1 seule ressource HTML par page (~25–34 Ko), 0 script externe, 0 erreur JS, aucun débordement horizontal, chargement complet 0,7–1,7 s |
| https://clientsici.fr/ | PageSpeed Insights via claude-seo `pagespeed_check.py`, 2026-11-05 | **Non mesuré** : « PSI rate limit exceeded » (quota sans clé API). Données terrain CrUX : non disponibles. Autorité et backlinks : non mesurés. |

Hypothèses (non vérifiées) : /maquette/ et /apercu/ sont destinés aux maquettes prospects ; un prospect non artisan se sent hors cible sur l'accueil ; la page autonome de la Veille fonctionne commercialement ; les filtres anti-spam pèsent la réputation des domaines liés.

## 6. À confirmer par vous

1. Cible de la refonte : artisans du bâtiment seulement, artisans + commerces locaux, ou toutes TPE ?
2. Modèle de prix : 79 €/mois sans frais initiaux, palier mensuel supérieur, ou forfait/devis ?
3. Les e-mails de prospection partent-ils d'un domaine secondaire ? Volume quotidien, liste « STOP » tenue ?
4. /maquette/ et /apercu/ contiennent-ils déjà des maquettes ? Avec noindex HTTP et jetons non devinables ?
5. Le CRM peut-il recevoir un formulaire supplémentaire étiqueté « refonte » avec « adresse du site actuel » et « secteur » ?
6. Existe-t-il des sites livrés ou des clients prêts à témoigner par écrit ?
7. Le vocabulaire des e-mails (« refonte », « refaire votre site », « votre site en HTTP ») : la page doit reprendre exactement le vôtre.

## 7. Limites

Analyse limitée aux 8 pages consultées. Pas de test auprès de prospects réels. Pas de mesure PageSpeed ni CrUX exploitable. Les occurrences de mots sont comptées sur le texte visible extrait, pas sur le HTML brut. Les affirmations sur le comportement des filtres anti-spam relèvent de connaissances générales, non mesurées ici.
