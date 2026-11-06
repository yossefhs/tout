# Héberger une maquette de prospect sur clientsici.fr : analyse et procédure

Question posée le 2026-11-05 : « Est-il adapté de faire ce projet sur clientsici.fr, sur une page propre au prospect ? »

## Verdict

**Oui, à condition que la page reste privée et clairement identifiée comme la vôtre.** Le site du prospect lui-même est exclu : aucune modification du site existant avant contrat (règle du brief, et vous n'en avez ni l'accès ni le mandat).

Constats sur clientsici.fr (lecture du 2026-11-05) : serveur Apache derrière l'infrastructure OVH (en-tête `x-iplb-*`), HTTPS avec HSTS actif, `X-Content-Type-Options: nosniff`, page d'accueil en `index, follow`. Un `.htaccess` par dossier devrait donc fonctionner (hypothèse à vérifier sur votre hébergement : AllowOverride).

## Pourquoi c'est adapté

- Votre offre indique déjà « Maquette présentée avant mise en ligne » : une page privée par prospect matérialise cette promesse.
- Votre domaine, votre responsabilité éditoriale : aucune confusion possible avec le site officiel du prospect si la page porte votre identité et le bandeau « Proposition non officielle ».
- La maquette livrée est autonome (un seul `index.html`, sans dépendance externe, sans tracker) : dépôt par FTP/SFTP suffisant.

## Conditions à respecter

1. **URL non devinable** : `https://clientsici.fr/apercu/<jeton-aleatoire-20-caracteres>/` plutôt que le nom de l'entreprise dans l'URL. Jamais de lien vers cette page depuis le reste du site, ni depuis le sitemap.
2. **Double directive noindex** : la balise `<meta name="robots" content="noindex, nofollow">` est déjà dans la maquette ; ajoutez l'en-tête serveur ci-dessous. Le noindex n'est pas un contrôle d'accès.
3. **Accès restreint recommandé** : mot de passe (Basic Auth) communiqué dans l'e-mail, ou page supprimée après la décision. Durée de vie conseillée : 30 jours.
4. **Aucune collecte** : le formulaire de la maquette est démonstratif (validation locale, aucun envoi). Ne branchez pas de formulaire réel ni d'analytics sur cette page. Vous évitez ainsi toute question RGPD sur des données de visiteurs.
5. **Droits sur les contenus** : pas de logo, photos ou textes du prospect sans autorisation explicite. Le nom commercial et l'activité, informations publiques, suffisent à la démonstration. Si vous obtenez l'autorisation, notez-la (date, canal) dans `04-livraison.md`.
6. **Identification** : la page affiche « Proposition non officielle — aperçu pour discussion » et votre nom/agence en pied de page.
7. **Nettoyage** : suppression du dossier après refus ou après signature (la maquette devient alors le vrai projet, sur le domaine du client).

## Exemple de `.htaccess` à placer dans `/apercu/<jeton>/`

```apache
# Interdire l'indexation au niveau HTTP (en plus de la balise meta de la page)
<IfModule mod_headers.c>
  Header set X-Robots-Tag "noindex, nofollow, noarchive"
</IfModule>

# Optionnel : accès par mot de passe (créer le fichier .htpasswd hors de la racine web)
# AuthType Basic
# AuthName "Aperçu prive"
# AuthUserFile /chemin/absolu/hors-web/.htpasswd
# Require valid-user

# Pas de listage de dossier
Options -Indexes
```

Et dans `robots.txt` du site : rien à ajouter. Un `Disallow` sur `/apercu/` rendrait le chemin visible dans un fichier public ; l'en-tête `X-Robots-Tag` suffit.

## Ce que je ne fais pas dans cette session

Aucune publication, aucun transfert vers clientsici.fr. Je livre `index.html` et cette procédure ; la mise en ligne est votre décision. Dans les messages de prospection, `{{LIEN_MAQUETTE}}` reste un champ à compléter avec l'URL privée que vous aurez créée.
