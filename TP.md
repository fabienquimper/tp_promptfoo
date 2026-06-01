# TP — Needle in a Haystack : évaluer la mémoire de position d'un LLM

## Objectif pédagogique

Comprendre expérimentalement comment un LLM gère l'information dans un contexte long.
Tu vas observer par toi-même le phénomène dit **"Lost in the Middle"** : la tendance des modèles
à mieux retenir ce qui est au début ou à la fin d'un document que ce qui est au milieu.

---

## Concept : le "Needle in a Haystack"

L'idée est simple : on cache une information précise (l'aiguille) dans un long texte (la botte de foin),
puis on demande au modèle de la retrouver. En variant la **position** de l'aiguille, on mesure l'impact
de la position sur la capacité de rappel.

```
┌─────────────────────────────────────────────┐
│  Ligne  1  : [bruit]                        │  ← DÉBUT
│  Ligne  2  : [bruit]                        │
│  Ligne  3  : 🎯 CIBLE ← le modèle la trouve │
│  ...                                        │
│  Ligne 20  : [bruit]                        │
│  Ligne 21  : 🎯 CIBLE ← difficile ?         │  ← MILIEU
│  ...                                        │
│  Ligne 38  : [bruit]                        │
│  Ligne 39  : 🎯 CIBLE ← le modèle la trouve │  ← FIN
│  Ligne 40  : [bruit]                        │
└─────────────────────────────────────────────┘
```

---

## Prérequis

- Docker installé et fonctionnel
- Python 3.8+ avec PyYAML (`pip install pyyaml`)
- Node.js 18+ avec npm — pour l'interface web (recommandée)
- Un LLM accessible via une API compatible OpenAI (`/v1/chat/completions`)
  - Local : Ollama, LM Studio, vLLM
  - Cloud (gratuit) : **Groq** → créer un compte sur [console.groq.com](https://console.groq.com), générer une clé API (commence par `gsk_`)

---

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd promptfoo

# 2. Configurer le LLM (copier et éditer)
cp .env.example .env
# → Renseigne LLM_BASE_URL, LLM_MODEL et LLM_API_KEY dans .env
#
# Exemple avec Groq (gratuit, sans GPU) :
#   LLM_BASE_URL=https://api.groq.com/openai
#   LLM_MODEL=llama-3.1-8b-instant
#   LLM_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# 3. Générer les données de test
python generate_tests.py          # Tests synthétiques (40 lignes de codes)
python generate_medical_tests.py  # Tests médicaux (compte rendu Mr. Durant)

# 4a. Interface web (recommandée — fonctionne sans Docker)
cd app && npm install && npm run dev
# → http://localhost:5173

# 4b. Viewer Promptfoo (nécessite Docker)
docker compose up -d
# → http://localhost:15500
```

---

## Expérience 1 — Tests synthétiques (codes alphanumériques)

### Description
20 tests avec un contexte de 40 lignes du type :
```
ID-2824A-45: ALBATROS
ID-5333B-68: KEID
...
ID-9499T-84: CASSIOPEE   ← la cible est cachée ici
...
```
Le modèle doit retrouver l'ID exact associé à un nom-code.

### Lancer les tests
```bash
docker exec -it promptfoo_local sh /app/eval.sh
```

### Questions d'observation

> **Q1.** Regarde la colonne de résultats. Les PASS se concentrent-ils dans une zone particulière
> du tableau (début, milieu, fin) ?

> **Q2.** Note le score global (X/20). À quoi t'attendais-tu pour un modèle "intelligent" ?

> **Q3.** Essaie de modifier `max_tokens` dans `promptfooconfig.yaml` (passe-le à 50, puis à 20).
> Relance à chaque fois. Qu'est-ce qui change ?

---

## Expérience 2 — Tests médicaux (compte rendu Mr. Durant)

> **Comment ça marche ?** Le fichier de config passé à `eval.sh` détermine quel jeu de tests est chargé :
> `promptfooconfig.yaml` → `tests.yaml` (synthétique) et `promptfooconfig.medical.yaml` → `medical_tests.yaml`.
> Si tu n'as pas encore généré les données médicales : `python generate_medical_tests.py`

### Description
Le **même** compte rendu médical de 87 lignes sert de base pour tous les tests.
À chaque test, deux informations sont insérées à des positions variables :
- Un **groupe sanguin** (ex: `O Rh positif (O+)`)
- Un **médicament** (ex: `Rosuvastatine 10 mg`)

Le modèle doit retrouver les **deux** valeurs dans une seule réponse.

### Répartition des 20 tests

| # | Groupe | Sang inséré à | Médicament inséré à |
|---|--------|--------------|---------------------|
| 1–4 | DÉBUT/DÉBUT | Lignes 9–12 | Lignes 14–17 |
| 5–8 | MILIEU/MILIEU | Lignes 37–43 | Lignes 47–62 |
| 9–12 | FIN/FIN | Lignes 73–77 | Lignes 78–85 |
| 13–16 | DÉBUT/FIN | Lignes 9–13 | Lignes 74–83 |
| 17–20 | FIN/DÉBUT | Lignes 72–80 | Lignes 10–14 |

### Lancer les tests
```bash
docker exec -it promptfoo_local sh /app/eval.sh /app/promptfooconfig.medical.yaml
```

### Questions d'observation

> **Q4.** Quels groupes (DÉBUT/DÉBUT, MILIEU/MILIEU, FIN/FIN, DÉBUT/FIN, FIN/DÉBUT)
> obtiennent les meilleurs scores ? Et les pires ?

> **Q5.** *(Modèles reasoning uniquement : Ministral, Deepseek R1, QwQ…)*
> Observe les réponses qui commencent par `[THINK]`. Que fait le modèle avant de répondre ?
> Est-ce une qualité ou un défaut dans ce contexte ?

> **Q6.** *(Modèles locaux via LM Studio uniquement)*
> Certaines réponses affichent `<SPECIAL_30>`. Cherche dans la documentation ce que
> cela signifie. Quelle est la conséquence sur le test ?

> **Q7.** Compare les scores entre les groupes **croisés** (DÉBUT/FIN et FIN/DÉBUT) et les
> groupes **alignés** (DÉBUT/DÉBUT, MILIEU/MILIEU, FIN/FIN). Qu'est-ce que cela révèle
> sur la stratégie de lecture du modèle ?

---

## Expérience 3 — Impact du paramètre `max_tokens`

### Protocole

Lance les tests médicaux avec **trois valeurs** de `max_tokens` et note les scores :

| `max_tokens` | Score observé | Observations |
|---|---|---|
| 50 | ? | |
| 150 | ? | |
| 800 | ? | |

Pour changer `max_tokens`, édite `promptfooconfig.medical.yaml` :
```yaml
config:
  max_tokens: 50   # ← change cette valeur
```
Puis relance :
```bash
docker exec -it promptfoo_local sh /app/eval.sh /app/promptfooconfig.medical.yaml
```

> **Q8.** À partir de quelle valeur les scores s'améliorent significativement ?
> Pourquoi `max_tokens` a-t-il autant d'impact sur ce modèle en particulier ?

> **Q9.** Calcule le ratio tokens de complétion / tokens de prompt pour chaque run
> (visible dans la ligne `Total Tokens` à la fin de l'eval). Que remarques-tu ?

---

## Expérience 4 — Changer de modèle (si disponible)

Si tu as accès à plusieurs modèles, teste le même jeu avec un modèle plus grand (7B, 13B…).

**Via l'interface web** — modifie `LLM_MODEL` dans `.env`, puis redémarre :
```bash
# Ctrl+C pour arrêter, puis relancer :
cd app && npm run dev
```

**Via Docker** — modifie `LLM_MODEL` dans `.env`, puis **recrée** le container :
```bash
docker compose up -d --force-recreate
docker exec -it promptfoo_local sh /app/eval.sh /app/promptfooconfig.medical.yaml
```

> **Q10.** Le score s'améliore-t-il ? Le biais de position est-il toujours présent ?
> Les `<SPECIAL_30>` disparaissent-ils ?

---

## Grille de résultats à remplir

### Tests synthétiques (Expérience 1)

| Modèle | max_tokens | DÉBUT (/6) | MILIEU (/8) | FIN (/6) | Score global (/20) |
|---|---|---|---|---|---|
| | 2000 | /6 | /8 | /6 | /20 |

### Tests médicaux (Expériences 2 et 3)

| Run | Modèle | max_tokens | Score global | DÉBUT/DÉBUT | MILIEU/MILIEU | FIN/FIN | DÉBUT/FIN | FIN/DÉBUT |
|---|---|---|---|---|---|---|---|---|
| 1 | | 150 | /20 | /4 | /4 | /4 | /4 | /4 |
| 2 | | 800 | /20 | /4 | /4 | /4 | /4 | /4 |
| 3 | | | /20 | /4 | /4 | /4 | /4 | /4 |

---

## Résultats de référence (à ne lire qu'après avoir fait tes propres tests !)

<details>
<summary>▶ Cliquer pour révéler les résultats de référence</summary>

Obtenus avec `mistralai/ministral-3-3b` via LM Studio.

### max_tokens = 150
```
Score : 3/20 (15%)

Cause : le modèle génère un raisonnement interne [THINK] avant de répondre.
Avec 150 tokens, il dépense tout son budget en réflexion et n'a plus de place
pour écrire la réponse. L'assertion ne trouve pas la valeur → FAIL.
```

### max_tokens = 800
```
Score : 15/20 (75%)

DÉBUT/DÉBUT   : 4/4 (100%) ✓
MILIEU/MILIEU : 4/4 (100%) ✓
FIN/FIN       : 4/4 (100%) ✓
DÉBUT/FIN     : 3/4  (75%) ~
FIN/DÉBUT     : 0/4   (0%) ✗

Les 5 échecs sont tous dans le groupe FIN/DÉBUT. Le modèle produit des tokens
spéciaux <SPECIAL_30> : il atteint la limite réelle de son contexte de génération
quand le sang est en fin de document ET que le raisonnement est très long.
```

### Interprétation

Le modèle gère bien les positions alignées (les deux cibles dans la même zone).
Il échoue sur les positions croisées FIN/DÉBUT, ce qui révèle que le modèle doit
parcourir tout le document pour la première cible (en fin) et que le raisonnement
consomme le budget de tokens avant d'arriver à la réponse.

Ce n'est pas un biais "Lost in the Middle" classique ici, mais un **biais de limite
de génération** : le modèle est capable de lire tout le document, mais son budget
de tokens de réponse est insuffisant pour les cas les plus complexes.

</details>

---

## Pour aller plus loin

- Modifie `N_LINES` dans `generate_tests.py` (passe à 20 ou 80 lignes) et observe l'impact
- Teste avec un modèle **sans** raisonnement interne : le [THINK] disparaît-il ?
- Compare les tokens de prompt entre les tests synthétiques et médicaux (`Total Tokens` dans l'eval)
- Consulte le [papier original "Lost in the Middle"](https://arxiv.org/abs/2307.03172) (Liu et al., 2023)
