#!/usr/bin/env python3
"""Utilitaire de configuration du pipeline Clients Ici.

  config_util.py ensure [chemin]      crée config.json s'il manque ; sinon n'ajoute que les clés (et sous-clés) absentes
  config_util.py get <clé> [chemin]   affiche une valeur (listes → jointes par des virgules, booléens → true/false)

Chemin par défaut : <pipeline>/config.json (le dossier parent de ce script).
"""
import json
import os
import sys

DEFAUTS = {
    "depts": ["28"],
    "nafs_artisans": ["43.22A", "43.22B", "43.21A", "43.32A", "43.34Z", "43.91A", "43.99C"],
    "nafs_commerces": ["96.02A", "10.71C", "47.24Z", "56.10A"],
    "max_par_requete": 100,
    "exclure_ei": False,
    # Clés propres au pipeline (ajoutées si absentes)
    "max_enrichissement": 60,
    "concurrence_enrichissement": 3,
    "utiliser_ddg": True,
    "siege_uniquement": True,
    "categorie": "PME",
    # Cible TPE (filter_queue.py) : effectif INSEE ≤ code (11 = 10 à 19 salariés ; vide/NN = gardé),
    # CA ≤ ca_max, établissements ouverts ≤ nb_etablissements_max, motifs exclus dans le nom/l'enseigne (mots entiers)
    "cible_tpe": {"effectif_max_code": "11", "ca_max": 2000000, "nb_etablissements_max": 2,
                  "motifs_exclus_nom": ["GROUPE", "HOLDING", "SAS INTERNATIONAL"]},
    # Clés des sessions planifiées (composant D : prospection-run / prospection-replies)
    "mode": "review",                 # review : brouillons Gmail à valider ; auto : envoi direct
    "plafond_quotidien": 10,
    "plafond_horaire": 4,
    "heures_envoi": {"debut": "09:00", "fin": "18:00", "jours": [0, 1, 2, 3, 4], "fuseau": "Europe/Paris"},
    "expediteur": {
        "nom": "Guillaume Samama",
        "agence": "Clients Ici",
        "entreprise": "Clients Ici",
        "email_reponse": "contact@clientsici.fr",
        "email": "contact@clientsici.fr",
        "tel": "07 56 97 45 75",
        "adresse": "6 rue du Parc, 28190 Landelles",
        "url_offre": "https://clientsici.fr/refonte-site-vitrine/",
        "url_confidentialite": "https://clientsici.fr/confidentialite/",
    },
    "page_refonte": "https://clientsici.fr/refonte-site-vitrine/",
    "maquette_base_url": "https://clientsici.fr",
    "maquette_lien_dans_email": False,  # true seulement quand le déploiement des aperçus (dépôt + Action FTP) est vérifié
    "libelle_gmail": "Prospection",
    "relance": {"activee": False, "delai_jours": 7, "max": 1},
    "accuser_reception_stop": False,
    "reponses_auto": "jamais",        # jamais | accuse_reception | complet (voir docs/00-cadre.md)
}

PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(PIPELINE_DIR, "config.json")


def charger(chemin):
    if not os.path.exists(chemin):
        return {}
    with open(chemin, encoding="utf-8") as f:
        contenu = f.read().strip()
    if not contenu:
        return {}
    data = json.loads(contenu)
    if not isinstance(data, dict):
        raise ValueError("config.json doit contenir un objet JSON")
    return data


def ensure(chemin):
    existait = os.path.exists(chemin)
    try:
        cfg = charger(chemin)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"ERREUR : {chemin} illisible ({e}). Corrige-le ou supprime-le.", file=sys.stderr)
        return 2
    ajoutees = [k for k in DEFAUTS if k not in cfg]
    for k in ajoutees:
        cfg[k] = DEFAUTS[k]
    # sous-clés manquantes des objets (expediteur, heures_envoi, relance, cible_tpe) : ajoutées sans toucher aux valeurs présentes
    for k, defaut in DEFAUTS.items():
        if isinstance(defaut, dict) and isinstance(cfg.get(k), dict):
            for sk, sv in defaut.items():
                if sk not in cfg[k]:
                    cfg[k][sk] = sv
                    ajoutees.append(f"{k}.{sk}")
    if ajoutees or not existait:
        os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            f.write("\n")
    print(json.dumps({"fichier": chemin, "cree": not existait, "cles_ajoutees": ajoutees}, ensure_ascii=False))
    return 0


def get(cle, chemin):
    cfg = charger(chemin)
    if cle not in cfg:
        print(f"ERREUR : clé absente : {cle}", file=sys.stderr)
        return 1
    v = cfg[cle]
    if isinstance(v, bool):
        print("true" if v else "false")
    elif isinstance(v, list):
        print(",".join(str(x) for x in v))
    else:
        print(v)
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "ensure":
        return ensure(argv[2] if len(argv) > 2 else DEFAULT_PATH)
    if cmd == "get":
        if len(argv) < 3:
            print("usage : config_util.py get <clé> [chemin]", file=sys.stderr)
            return 1
        return get(argv[2], argv[3] if len(argv) > 3 else DEFAULT_PATH)
    print(f"commande inconnue : {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
