# Origine de chaque champ de spec.json (lead rabarot-freres.fr → https://rabarot-freres.fr/)

| Champ | Valeur | Source |
|---|---|---|
| nom | Rabarot Frères | lead.json nom « RABAROT FRERES » (enseigne vide), casse normale ; concorde avec pages[0].title « Rabarot Frères - Couvreur RGE Qualibat à Angerville » et pages[0].h1 « RABAROT FRERES » ; correspondance_entreprise.details.nom.trouve = true |
| metier | Travaux de maçonnerie générale et gros œuvre de bâtiment | lead.json libelle_naf (NAF 43.99C) |
| metier_court | Entreprise de maçonnerie | libellé court courant du NAF 43.99C ; forme reprise du site (pages[0].h3 « Entreprise de maçonnerie : agrandissez ou rénovez votre maison… ») |
| ville | Gommerville | a_preserver.coordonnees.adresses[0].ville « Gommerville » (28310) ; concorde avec lead.ville GOMMERVILLE et lead.cp 28310 ; correspondance_entreprise : ville et cp retrouvés sur l'accueil |
| adresse | 3 Rue du Château, 28310 Gommerville | a_preserver.coordonnees.adresses[0] (rue, code_postal, ville) ; concorde avec lead.adresse « 3 RUE DU CHATEAU 28310 GOMMERVILLE » |
| tel | 02 37 99 52 16 | a_preserver.coordonnees.telephones[0] ; pages[1].liens_tel « tel:02 37 99 52 16 » (page contact) ; = lead.tel |
| email | rabarot-freres@orange.fr | lead.email, présent dans a_preserver.coordonnees.emails[0] |
| slogan | Travaux de rénovation - maçonnerie - couverture du bâtiment | pages[0].h1[4] (accueil), cité tel quel ; décrit l'activité |
| services | Maçonnerie ; Couverture ; Charpente ; Plâtrerie ; Menuiseries ; Extension | a_preserver.services_listes (H3 sous le H2 « Découvrez nos prestations » de l'accueil), libellés inchangés ; 6 retenus sur 8 (« Clôtures » et « Fenêtre de toit » omis par la limite de 6) ; écartés car non prestations : « Entreprise familiale », « RGE Qualibat », « Garantie décennale », « Écoute et proximité » (H3 de « Les raisons de nous faire confiance ») |
| preuves_verifiees | RGE Qualibat mentionné sur le site ; Garantie décennale mentionnée sur le site ; Entreprise familiale depuis 1948 (mention du site) | pages[0].title et pages[0].h3 « RGE Qualibat » ; pages[0].h3 « Garantie décennale » ; pages[0].h1 « ENTREPRISE artisanale DEPUIS 1948 » et pages[2].h1 « ENTREPRISE FAMILIALE DEPUIS 1948 » (a-propos) |
| zone | omis | aucune phrase de zone d'intervention relevée dans audit.json (departements_mentionnes « Eure-et-Loir » sur a-propos, titres « à Angerville » / « proche de Pussay » : pas une phrase citable telle quelle) |
| horaires | omis | la page contact a un H3 « heures d'ouverture » et l'accueil un JSON-LD OpeningHoursSpecification, mais les valeurs ne sont pas relevées dans audit.json |
| palette / objectif | batiment / devis | NAF 43.99C ∈ config.nafs_artisans |
| domaine_source | rabarot-freres.fr | cible.domaine_final (= domaine_demande, aucune redirection) |
