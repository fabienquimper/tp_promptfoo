# Needle in a Haystack — Évaluation LLM avec Promptfoo

Mesure la capacité d'un LLM à retrouver une information précise cachée à différentes **positions** dans un contexte de 40 lignes.

> **Étudiant ?** → Consulte [`TP.md`](TP.md) pour le guide de travaux pratiques guidé.

## Concept

Le test insère un ID secret (`ID-XXXX?-XX`) associé à un nom-code dans un bloc de 40 entrées. Le LLM doit retrouver l'ID exact. Les tests sont répartis en trois groupes pour révéler le **biais de position** du modèle :

| Groupe | Position dans les 40 lignes | Assertion |
|---|---|---|
| DÉBUT | Lignes 1 – 5 | `equals` (réponse exacte) |
| MILIEU | Lignes 15 – 25 | `icontains` (tolère une phrase) |
| FIN | Lignes 36 – 40 | `equals` (réponse exacte) |

---

## Prérequis

- [Docker](https://docs.docker.com/get-docker/) + Compose v2
- Python 3.8+ avec PyYAML (`pip install pyyaml`)
- Node.js 18+ avec npm — uniquement pour l'interface web (`cd app && npm install`)
- Un LLM accessible via une API compatible OpenAI (`/v1/chat/completions`)

---

## Installation

```bash
git clone <ce-repo>
cd promptfoo

# 1. Génère les données de test (une seule fois, seed fixe = reproductible)
python generate_tests.py

# 2. Configure ton LLM
cp .env.example .env
# Edite .env selon ton cas (voir section Configuration)

# 3. Lance le viewer Promptfoo
docker compose up -d

# 4. Lance les 20 tests
docker exec -it promptfoo_local sh /app/eval.sh

# 5. Ouvre les résultats
#    http://localhost:15500
```

---

## Configuration LLM

Toute la configuration passe par le fichier `.env`. Copie `.env.example` et décommente le cas qui correspond.

### Cas 1 — LLM sur la même machine (localhost)

Le LLM tourne sur ta machine de travail (Ollama, LM Studio…).

```dotenv
LLM_MODEL=mistral
LLM_BASE_URL=http://host.docker.internal:11434
```

> `host.docker.internal` est l'alias Docker pour atteindre `localhost` de la machine hôte.
> Sur Linux/WSL, le `extra_hosts` dans `docker-compose.yml` le résout automatiquement.

**Vérification** (depuis ta machine) :
```bash
curl http://localhost:11434/v1/models
```

---

### Cas 2 — LLM sur une autre machine du réseau local

Le LLM tourne sur un serveur ou un NAS de ton réseau domestique/pro.

```dotenv
LLM_MODEL=llama3
LLM_BASE_URL=http://192.168.1.42:11434
```

Remplace `192.168.1.42` par l'IP LAN réelle de la machine cible.

**Trouver l'IP LAN de la machine cible :**
```bash
# Linux / macOS
ip a | grep "inet " | grep -v 127
# Windows
ipconfig | findstr "IPv4"
```

**Vérification** (depuis ta machine) :
```bash
curl http://192.168.1.42:11434/v1/models
```

> Si la connexion échoue, vérifie que le pare-feu de la machine cible autorise le port.
> Pour Ollama : `OLLAMA_HOST=0.0.0.0 ollama serve` pour écouter sur toutes les interfaces.

---

### Cas 3 — API distante (cloud)

Le LLM est hébergé sur un service externe. La clé API est injectée automatiquement dans l'en-tête `Authorization`.

**OpenAI :**
```dotenv
LLM_BASE_URL=https://api.openai.com
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
```

**Mistral AI :**
```dotenv
LLM_BASE_URL=https://api.mistral.ai
LLM_MODEL=mistral-small-latest
LLM_API_KEY=xxxxxxxxxxxxxxxxxxxx
```

**OpenRouter** (accès à des dizaines de modèles) :
```dotenv
LLM_BASE_URL=https://openrouter.ai/api
LLM_MODEL=meta-llama/llama-3-8b-instruct
LLM_API_KEY=sk-or-xxxxxxxxxxxxxxxxxxxx
```

---

## Lancer les tests

```bash
# Évaluation complète (20 tests synthétiques)
docker exec -it promptfoo_local sh /app/eval.sh

# Tests médicaux
docker exec -it promptfoo_local sh /app/eval.sh /app/promptfooconfig.medical.yaml
```

> `eval.sh` contourne un bug de promptfoo : `{{env.LLM_MODEL}}` n'est pas résolu dans la section `providers` — le script substitue la valeur avant d'appeler promptfoo.

---

## Lire les résultats

Ouvre **http://localhost:15500** après l'évaluation.

```
Score global :  12/20  (60%)
┌────────────┬──────────┬────────┐
│  Groupe    │ Réussis  │  Score │
├────────────┼──────────┼────────┤
│  DÉBUT     │  6/6     │  100%  │  ← le modèle retient bien le début
│  MILIEU    │  3/8     │   37%  │  ← biais de position visible
│  FIN       │  3/6     │   50%  │
└────────────┴──────────┴────────┘
```

**Interpréter :**
- Score MILIEU < DÉBUT/FIN → biais "Lost in the Middle" classique
- Score DÉBUT < FIN → le modèle privilégie les tokens récents (biais de recency)
- Assertion `equals` échoue mais `icontains` passerait → le modèle donne la bonne valeur mais avec trop de verbosité

**Signaux importants à surveiller :**

| Signal dans la réponse | Cause | Action |
|---|---|---|
| `[THINK]...` puis réponse correcte | Modèle reasoning, tokens suffisants | Normal |
| `[THINK]...` puis réponse tronquée | `max_tokens` trop petit | Augmenter `max_tokens` |
| `<SPECIAL_30><SPECIAL_30>...` | Modèle atteint la limite réelle de génération | Réduire la taille du contexte ou changer de modèle |
| Réponse vide | `max_tokens` très bas ou erreur serveur | Vérifier les logs |

**Exporter les résultats :**
- Bouton **Export** dans l'interface → JSON ou CSV
- Ou en CLI : `docker exec -it promptfoo_local sh -c "sh /app/eval.sh && promptfoo eval --output /app/results.json"`

---

## Résultats de référence — `mistralai/ministral-3-3b` (tests médicaux)

| Run | `max_tokens` | Score | DÉBUT/DÉBUT | MILIEU/MILIEU | FIN/FIN | DÉBUT/FIN | FIN/DÉBUT |
|---|---|---|---|---|---|---|---|
| 1 | 150 | **3/20 (15%)** | 1/4 | 1/4 | 0/4 | 1/4 | 0/4 |
| 2 | 800 | **15/20 (75%)** | 4/4 ✓ | 4/4 ✓ | 4/4 ✓ | 3/4 ~ | 0/4 ✗ |

**Enseignements clés :**
- Le paramètre `max_tokens` est critique pour les modèles de type *reasoning* : ils génèrent un raisonnement interne `[THINK]` avant de répondre, ce qui consomme une partie du budget
- Les groupes **alignés** (deux cibles dans la même zone) passent à 100% une fois le budget corrigé
- Le groupe **FIN/DÉBUT** (cibles aux extrémités opposées) échoue à 0% : le raisonnement devient trop long et le modèle atteint sa limite de génération (`<SPECIAL_30>`)
- Ce n'est pas le "Lost in the Middle" classique mais un **biais de limite de génération** propre aux petits modèles reasoning

---

## Regénérer les données de test

Les tests sont déterministes (seed Python fixé à `42`). Relancer le script produit exactement le même `tests.yaml` :

```bash
python generate_tests.py
```

Pour créer une nouvelle série de tests avec des données différentes, change `SEED` en tête de `generate_tests.py`.

---

## Jeu de test médical — Compte rendu Mr. Durant

Un deuxième jeu de tests plus réaliste : le **même** document médical de 87 lignes sert de base pour tous les tests. À chaque test, deux informations sont injectées à des positions variables :

- le **groupe sanguin** (8 valeurs possibles : O+, A-, B+, AB-, O-, A+, B-, AB+)
- un **médicament prescrit** (20 molécules différentes)

Le LLM doit retrouver les deux valeurs dans un seul appel.

### Répartition des 20 tests

| Groupe | Sang inséré à | Médicament inséré à | Nb |
|---|---|---|---|
| DÉBUT/DÉBUT | lignes 9–12 | lignes 14–17 | 4 |
| MILIEU/MILIEU | lignes 37–43 | lignes 47–62 | 4 |
| FIN/FIN | lignes 73–77 | lignes 78–85 | 4 |
| DÉBUT/FIN | lignes 9–13 | lignes 74–83 | 4 |
| FIN/DÉBUT | lignes 72–80 | lignes 10–14 | 4 |

Les 4 derniers groupes (croisés) sont les plus difficiles : les deux cibles sont aux extrémités opposées du document.

### Lancer les tests médicaux

```bash
# 1. Générer les données (une seule fois)
python generate_medical_tests.py

# 2. Évaluer
docker exec -it promptfoo_local sh /app/eval.sh /app/promptfooconfig.medical.yaml

# 3. Résultats sur http://localhost:15500
```

### Assertions

Chaque test vérifie deux conditions :
- `icontains "O+"` (forme courte du groupe sanguin, non-ambiguë)
- `icontains "Rosuvastatine 10 mg"` (nom + dosage exact du médicament)

Un test est **vert** uniquement si le LLM retourne les **deux** valeurs correctes.

---

## Interface web (alternative à la ligne de commande)

Une application Vue 3 / Node.js permet de visualiser, éditer et exécuter les tests directement dans le navigateur, sans passer par `docker exec`.

### Démarrage

```bash
cd app
npm install   # une seule fois
npm run dev   # backend :3000 + frontend :5173
```

Ouvre **http://localhost:5173**.

> En production : `npm run build && node server.js` (tout sur `:3000`)

### Fonctionnalités

| Zone | Description |
|---|---|
| **En-tête** | Modèle, URL du LLM, indicateur de connexion, bouton ping |
| **Sélecteur** | Bascule entre `promptfooconfig.yaml` et `promptfooconfig.medical.yaml` |
| **Tableau** | Groupe (chip coloré), cible, résultat attendu, boutons Run / Éditer, résultat PASS/FAIL |
| **Tout exécuter** | Lance tous les tests séquentiellement avec barre de progression en temps réel |
| **Dialog résultat** | Prompt rendu complet, réponse brute du LLM, usage de tokens |
| **Dialog édition** | Modifie les variables et assertions, sauvegarde dans le fichier YAML |

Le backend lit le `.env` du dossier parent — aucune configuration supplémentaire nécessaire.

---

## Structure des fichiers

```
promptfoo/
├── docker-compose.yml              # Container Promptfoo (viewer + résultats)
├── eval.sh                         # Wrapper d'évaluation (contourne le bug LLM_MODEL)
├── promptfooconfig.yaml            # Tests synthétiques (codes alphanumériques)
├── promptfooconfig.medical.yaml    # Tests médicaux (compte rendu Mr. Durant)
├── generate_tests.py               # Générateur synthétique (seed 42)
├── generate_medical_tests.py       # Générateur médical
├── .env.example                    # Modèle de configuration LLM
├── .env                            # Ta config locale (non versionné)
└── app/                            # Interface web Vue 3 + Node
    ├── server.js                   # Backend Express (API + proxy LLM)
    ├── src/
    │   ├── App.vue
    │   └── components/
    │       ├── LlmBar.vue          # Statut connexion LLM
    │       ├── TestRunner.vue      # Tableau de tests + run
    │       └── EditDialog.vue      # Édition d'un test
    └── package.json
```

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `The model {{env.llm_model}} does not exist` | Promptfoo ne résout pas `{{env.LLM_MODEL}}` dans la config provider | Utilise `docker exec -it promptfoo_local sh /app/eval.sh` au lieu de `promptfoo eval` directement |
| `Connection refused` depuis le container | `host.docker.internal` ne résout pas | Vérifie `extra_hosts` dans compose, ou utilise l'IP LAN |
| `401 Unauthorized` | Clé API absente ou invalide | Renseigne `LLM_API_KEY` dans `.env` |
| `tests.yaml not found` | Script non exécuté | Lance `python generate_tests.py` |
| `medical_tests.yaml not found` | Script non exécuté | Lance `python generate_medical_tests.py` |
| Toutes les réponses sont vides | `max_tokens: 50` trop court ? | Augmente `max_tokens` dans `promptfooconfig.yaml` |
| Score MILIEU très bas | Comportement normal pour les petits modèles | C'est précisément ce que ce test mesure |
| App : `Cannot find module` au démarrage | `npm install` non exécuté | Lance `cd app && npm install` |
| App : LLM non accessible | `.env` absent ou `LLM_BASE_URL` incorrect | Vérifie le `.env` à la racine du projet |
