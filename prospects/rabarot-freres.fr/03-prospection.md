# 03 — Messages de prospection (générés par la chaîne, non envoyés)

Destinataire : voir lead.json (adresse publique relevée sur le site). Constats utilisés : C02, C03.

## Objets

- affichage mobile de rabarot-freres.fr
- rabarot-freres.fr sur téléphone

## E-mail (texte brut)

```
Bonjour,

J'ai testé l'affichage de rabarot-freres.fr sur téléphone, comme le verrait un client qui vous cherche. Sur un écran de téléphone, la page déborde à droite et certains textes sont coupés. Autre point : la page s'affiche un peu lentement sur téléphone : rien de grave, mais on peut faire plus léger.

Une page qui s'affiche vite, avec votre métier, votre ville et un numéro cliquable en haut, c'est un visiteur qui vous appelle au lieu de revenir à la liste.

Si cela vous intéresse, je vous montre à quoi ressemblerait votre page d'accueil refaite, avant toute décision et sans frais.

Est-ce que je vous la prépare ?

Guillaume Samama
Clients Ici
https://clientsici.fr/refonte-site-vitrine/
contact@clientsici.fr
6 rue du Parc, 28190 Landelles

--
Pourquoi ce message : vos coordonnées viennent de votre site rabarot-freres.fr, qui est public.
Pour ne plus recevoir de message, répondez STOP et je vous retire de ma liste.
Confidentialité : https://clientsici.fr/confidentialite/

```

Nombre de mots (méthode : pipeline/docs/03) : n.c..

## WhatsApp — brouillon, conditions de contact à vérifier

{"texte": "Bonjour, Guillaume de Clients Ici (Landelles). J'ai testé votre site rabarot-freres.fr sur téléphone : la page déborde de l'écran du téléphone. Je peux vous montrer une maquette de votre page d'accueil, sans engagement. Vous voulez la voir ?", "statut": "brouillon — conditions de contact à vérifier", "nb_caracteres": 241}

## SMS — brouillon, conditions de contact à vérifier

{"texte": "Bonjour, Guillaume (Clients Ici). Sur votre site rabarot-freres.fr : la page déborde de l'écran du téléphone. Maquette de votre page d'accueil possible, sans engagement. Intéressé ? STOP pour ne plus recevoir.", "statut": "brouillon — conditions de contact à vérifier", "nb_caracteres": 209}

## Avant envoi

- Expéditeur à choisir : guillaume@clientsici.fr via Brevo ou SMTP OVH (config.envoi), ou brouillon Gmail.
- `{{LIEN_MAQUETTE}}` : non inséré tant que l'aperçu n'est pas publié (config.maquette_lien_dans_email = false).
- Un numéro public n'est pas une autorisation WhatsApp ; SMS seulement si le canal est validé.