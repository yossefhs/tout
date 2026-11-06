# Origine de chaque champ de spec.json (lead grouperoyenergie.com → www.gre-enr.fr)

| Champ | Valeur | Source dans audit.json |
|---|---|---|
| nom | Groupe Roy Énergie | pages[0].h1 « GROUPE ROY ÉNERGIE … », pages[1..4].title « … | Groupe Roy Énergie » (casse normalisée) ; concorde avec lead.json nom |
| metier / slogan | Installateur de panneaux photovoltaïques | pages[0].h1 « GROUPE ROY ÉNERGIE Installateur de panneaux photovoltaïques » |
| metier_court | Installateur photovoltaïque | pages[0].title « expert photovoltaïque » ; H1 ci-dessus |
| ville | Toury | a_preserver.coordonnees.adresses[0] (28310 TOURY) ; concorde avec lead.cp 28310 |
| tel | 02 38 80 18 01 | pages[*].liens_tel « tel:0238801801 » (présent sur les 5 pages) ; concorde avec lead.tel. NB : telephones[0] = « 05 20 26 09 15 » est un faux positif regex (accueil seulement, aucun lien tel:) |
| email | contact@gre-enr.fr | a_preserver.coordonnees.emails[0] = lead.email |
| adresse | 23 rue Gondrelier, Z.A de la Haute Borne, 28310 Toury | a_preserver.coordonnees.adresses[0] (ville « TOURY Itinéraire » nettoyée : « Itinéraire » est le libellé d'un lien Google Maps collé à la ville) |
| services | Autoconsommation ; Revente totale ; Location de toiture ; Dépannage et Maintenance | a_preserver.menu (libellés inchangés) ; services_listes ne contient aucune prestation exploitable (titres de formulaire, slogans) |
| horaires, zone, preuves_verifiees | omis | non relevés explicitement (departements_mentionnes = liste déroulante de formulaire, pas une zone) |
| palette / objectif | batiment / devis | NAF 43.22B ∈ nafs_artisans |
| domaine_source | gre-enr.fr | cible.url_finale https://www.gre-enr.fr/ (grouperoyenergie.com redirige en 301) |
