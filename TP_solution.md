# TP — CORRECTION — Needle in a Haystack : évaluer la mémoire de position d'un LLM

> **Ce document est la correction complète du TP.**
> Il reprend l'intégralité du sujet et ajoute les réponses attendues (Q1–Q10),
> la grille de résultats de référence et une synthèse pédagogique.
>
> **Ne lis pas ce fichier avant d'avoir tenté les expériences par toi-même !**

---

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
  - Exemples : Ollama, LM Studio, vLLM, ou une API cloud (OpenAI, Mistral, Groq…)

---

## Installation

```bash
# 1. Cloner le dépôt
git clone <url-du-repo>
cd promptfoo

# 2. Configurer le LLM (copier et éditer)
cp .env.example .env
# → Renseigne LLM_BASE_URL et LLM_MODEL dans .env

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

### Questions d'observation — avec réponses

> **Q1.** Regarde la colonne de résultats. Les PASS se concentrent-ils dans une zone particulière
> du tableau (début, milieu, fin) ?

**Réponse Q1 :** Cela dépend du modèle utilisé.

- Avec un **modèle performant** (7B+, ou API cloud comme GPT-4o-mini, Llama 3.1 8B sur Groq) et
  `max_tokens` suffisant : le score est souvent **20/20**, sans biais visible. Le contexte de 40 lignes
  est trivial pour ces modèles.
- Avec un **petit modèle local** (3B) ou des paramètres sous-dimensionnés : les PASS se concentrent
  aux **extrémités** (DÉBUT et FIN). Les lignes 15–25 (MILIEU) sont sous-représentées en succès.

C'est le biais **"Lost in the Middle"** : les LLMs accordent naturellement plus d'attention aux tokens
proches du début (effet de primauté) et de la fin (effet de récence) du contexte. Les informations au
milieu sont statistiquement moins bien rappelées.

---

> **Q2.** Note le score global (X/20). À quoi t'attendais-tu pour un modèle "intelligent" ?

**Réponse Q2 :** On attendrait instinctivement **20/20** — un humain ne "perdrait" aucune information
dans un texte de 40 lignes.

Résultats typiques observés :
| Modèle | Score attendu |
|---|---|
| GPT-4o-mini, Llama 3.1 8B (cloud) | 19–20/20 |
| Modèle local 7B bien configuré | 15–19/20 |
| Modèle local 3B (Ministral) | 10–16/20 selon max_tokens |

L'écart par rapport à 20/20 est en soi une **mesure de la limite du modèle** sur cette tâche.
Un score parfait ne signifie pas que le modèle est "intelligent" — il signifie simplement que
le contexte de 40 lignes est dans sa fenêtre de confort.

---

> **Q3.** Essaie de modifier `max_tokens` dans `promptfooconfig.yaml` (passe-le à 50, puis à 20).
> Relance à chaque fois. Qu'est-ce qui change ?

**Réponse Q3 :**

- **`max_tokens = 50`** : pour un modèle *non-reasoning*, 50 tokens suffisent pour un ID (`ID-XXXX?-XX`
  fait ~4 tokens). Le score reste similaire. Pour un modèle *reasoning* (qui génère du `[THINK]`),
  le raisonnement interne consomme tout le budget → réponse tronquée → score proche de 0/20.

- **`max_tokens = 20`** : suffisant si le modèle répond directement par l'ID. Insuffisant si le modèle
  formule une phrase introductive ("L'ID associé à CASSIOPEE est...") → la réponse est coupée → FAIL.

**Conclusion clé :** `max_tokens` n'est pas qu'un paramètre de performance — c'est un paramètre
**fonctionnel critique** pour les modèles reasoning. Un budget insuffisant donne zéro résultat,
pas un résultat dégradé.

---

## Expérience 2 — Tests médicaux (compte rendu Mr. Durant)

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

### Questions d'observation — avec réponses

> **Q4.** Quels groupes (DÉBUT/DÉBUT, MILIEU/MILIEU, FIN/FIN, DÉBUT/FIN, FIN/DÉBUT)
> obtiennent les meilleurs scores ? Et les pires ?

**Réponse Q4 :** (basée sur `ministralai/ministral-3-3b` avec `max_tokens = 800`)

| Groupe | Score | Interprétation |
|---|---|---|
| DÉBUT/DÉBUT | **4/4 (100%)** ✓ | Les deux cibles sont proches en début de doc |
| MILIEU/MILIEU | **4/4 (100%)** ✓ | Les deux cibles sont proches au milieu |
| FIN/FIN | **4/4 (100%)** ✓ | Les deux cibles sont proches en fin de doc |
| DÉBUT/FIN | **3/4 (75%)** ~ | Les cibles sont éloignées mais accessibles |
| **FIN/DÉBUT** | **0/4 (0%)** ✗ | Cas le plus difficile : voir Q7 |

**Meilleurs** : les trois groupes alignés (cibles dans la même zone).
**Pires** : FIN/DÉBUT, avec un échec systématique.

---

> **Q5.** *(Modèles reasoning uniquement : Ministral, Deepseek R1, QwQ…)*
> Observe les réponses qui commencent par `[THINK]`. Que fait le modèle avant de répondre ?
> Est-ce une qualité ou un défaut dans ce contexte ?

**Réponse Q5 :** Le bloc `[THINK]` est le **raisonnement interne du modèle** (*chain-of-thought*
automatique). Avant de répondre, le modèle "pense" à voix haute : il identifie les sections pertinentes
du document, relit les passages clés, formule sa réponse mentalement.

- **Qualité** : améliore la précision sur les contextes complexes. Le modèle ne répond pas "à
  l'instinct" — il structure sa démarche.
- **Défaut dans ce contexte** : le raisonnement consomme des tokens de complétion. Avec un budget
  limité (ex: 150 tokens), le raisonnement occupe 100–150 tokens et la réponse finale n'est jamais
  écrite → FAIL systématique.

*Note : ce comportement est propre aux modèles "reasoning" (Ministral 3B, Deepseek R1, QwQ 32B…).
Avec `llama-3.1-8b-instant` sur Groq ou `gpt-4o-mini`, le `[THINK]` n'apparaît pas.*

---

> **Q6.** *(Modèles locaux via LM Studio uniquement)*
> Certaines réponses affichent `<SPECIAL_30>`. Cherche dans la documentation ce que
> cela signifie. Quelle est la conséquence sur le test ?

**Réponse Q6 :** `<SPECIAL_30>` est un **token spécial de fin de génération** produit par certains
modèles au format Mistral servis via LM Studio. Il indique que le modèle a atteint sa **limite
physique de génération** — la réponse est coupée à ce point, le reste est perdu.

Conséquence directe : l'assertion `icontains` ne trouve ni le groupe sanguin ni le médicament
dans la réponse → **FAIL systématique**, quelle que soit la qualité du raisonnement précédent.

Ce phénomène ne se produit pas avec les APIs cloud (Groq, OpenAI, Mistral AI) qui gèrent la
génération côté serveur sans cette limitation.

---

> **Q7.** Compare les scores entre les groupes **croisés** (DÉBUT/FIN et FIN/DÉBUT) et les
> groupes **alignés** (DÉBUT/DÉBUT, MILIEU/MILIEU, FIN/FIN). Qu'est-ce que cela révèle
> sur la stratégie de lecture du modèle ?

**Réponse Q7 :**

| Type | Score total | Détail |
|---|---|---|
| Groupes alignés | **12/12 (100%)** | DÉBUT/DÉBUT + MILIEU/MILIEU + FIN/FIN |
| Groupes croisés | **3/8 (37%)** | DÉBUT/FIN + FIN/DÉBUT |

**Ce que ça révèle :**

Les groupes alignés passent parfaitement → le modèle *peut* lire le milieu du document (MILIEU/MILIEU
= 4/4). Le problème n'est donc **pas** une incapacité à lire le milieu.

Le problème des groupes croisés, et surtout de FIN/DÉBUT, est le **coût cognitif de relier deux
informations éloignées**. Quand le groupe sanguin est en fin de document, le modèle doit "parcourir"
mentalement tout le texte avant de le trouver. Cela génère un raisonnement `[THINK]` très long qui
épuise le budget de tokens avant d'arriver à la réponse finale.

**Ce n'est pas le "Lost in the Middle" classique ici — c'est un biais de limite de génération.**

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

### Résultats de référence — `ministralai/ministral-3-3b` via LM Studio

| `max_tokens` | Score observé | Observations |
|---|---|---|
| 50 | **0/20 (0%)** | Le raisonnement `[THINK]` consomme tout le budget ; réponse vide ou tronquée |
| 150 | **3/20 (15%)** | Quelques cas très simples passent ; la plupart tronqués en plein raisonnement |
| 800 | **15/20 (75%)** | Tous les cas alignés passent ; FIN/DÉBUT échoue avec `<SPECIAL_30>` |

---

> **Q8.** À partir de quelle valeur les scores s'améliorent significativement ?
> Pourquoi `max_tokens` a-t-il autant d'impact sur ce modèle en particulier ?

**Réponse Q8 :** L'amélioration significative se produit **entre 150 et 800 tokens**. À 150, seuls 3/20
passent (les cas où le raisonnement est très court). À partir de ~400 tokens, les cas alignés
commencent à passer. L'amélioration n'est pas linéaire — il y a un **seuil** autour de 300–400 tokens
en dessous duquel presque tout échoue.

`max_tokens` impacte autant ce modèle parce que c'est un modèle **reasoning** : il génère un bloc
`[THINK]` de 100–300 tokens avant d'écrire la réponse finale (~15 tokens). Les modèles non-reasoning
(Llama instruct, GPT) n'ont pas ce surcoût — 50 tokens leur suffisent.

**Analogie** : c'est comme demander à quelqu'un de résoudre un problème de maths en montrant tous les
calculs intermédiaires, mais en limitant l'espace à 3 lignes de papier.

---

> **Q9.** Calcule le ratio tokens de complétion / tokens de prompt pour chaque run
> (visible dans la ligne `Total Tokens` à la fin de l'eval). Que remarques-tu ?

**Réponse Q9 :** Les tokens de **prompt** sont environ 500–800 pour les médicaux (contre ~280 pour les
synthétiques) — le document médical de 87 lignes est ~3× plus long.

Les tokens de **complétion** attendus sont très faibles théoriquement (~15–20 tokens pour 2 lignes
de réponse). Mais en pratique, avec un modèle reasoning :

| Run | max_tokens | Ratio complétion/prompt (approx.) |
|---|---|---|
| Synthétiques | 2000 | ~0.05 — réponse directe, pas de [THINK] |
| Médicaux, max=800 | 800 | ~0.30–0.60 — raisonnement [THINK] dominant |

Un ratio complétion/prompt élevé indique que **le modèle "pense" plus qu'il ne "répond"**.
C'est un signal direct du coût cognitif de la tâche : plus les deux cibles sont éloignées,
plus le raisonnement est long.

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

**Réponse Q10 :**

| Aspect | Modèle plus grand (7B+) | Modèle non-reasoning |
|---|---|---|
| Score global | Oui, en général 17–20/20 | Oui, souvent 18–20/20 |
| Biais de position | Atténué mais présent sur contextes > 100 lignes | Atténué |
| `<SPECIAL_30>` | Disparaît avec les APIs cloud | Disparaît — pas de limite physique de génération |
| `[THINK]` | Persiste si le modèle est toujours de type reasoning | Disparaît — pas de chaîne de pensée automatique |
| `max_tokens = 150` suffit ? | Non pour un reasoning 7B | **Oui** pour un instruct 7B sans reasoning |

**Conclusion :** Les `<SPECIAL_30>` disparaissent car ils sont propres aux contraintes matérielles des
petits modèles locaux. Un modèle non-reasoning (Llama 3 8B, GPT-4o-mini) obtient souvent 18–20/20
avec `max_tokens = 150` là où Ministral 3B scoring en fait 3/20.

---

## Grille de résultats — Référence complète

### Tests synthétiques

| Modèle | max_tokens | DÉBUT (/6) | MILIEU (/8) | FIN (/6) | Score global (/20) |
|---|---|---|---|---|---|
| ministral-3b (LM Studio) | 2000 | 6/6 ✓ | 5–7/8 ~ | 6/6 ✓ | 17–19/20 |
| llama-3.1-8b (Groq) | 2000 | 6/6 ✓ | 8/8 ✓ | 6/6 ✓ | 20/20 ✓ |

*Note : le MILIEU utilise l'assertion `icontains` (plus souple) car les petits modèles ont tendance
à reformuler la réponse plutôt qu'à donner l'ID seul.*

### Tests médicaux (Expériences 2 et 3)

| Run | Modèle | max_tokens | Score global | DÉBUT/DÉBUT | MILIEU/MILIEU | FIN/FIN | DÉBUT/FIN | FIN/DÉBUT |
|---|---|---|---|---|---|---|---|---|
| 1 | ministral-3b | 150 | **3/20 (15%)** | 1/4 | 1/4 | 0/4 | 1/4 | 0/4 |
| 2 | ministral-3b | 800 | **15/20 (75%)** | 4/4 ✓ | 4/4 ✓ | 4/4 ✓ | 3/4 ~ | 0/4 ✗ |
| 3 | llama-3.1-8b (Groq) | 800 | **18–20/20** | 4/4 ✓ | 4/4 ✓ | 4/4 ✓ | 4/4 ✓ | 2–4/4 ~ |

---

## Synthèse pédagogique

### Ce que ces tests mesurent vraiment

Le titre du TP annonce "Lost in the Middle" — mais les résultats révèlent un phénomène plus nuancé
selon l'architecture du modèle.

**Avec un modèle reasoning (Ministral 3B) :**

Le modèle lit bien tout le document — MILIEU/MILIEU passe à 4/4 (100%) avec le bon budget de tokens.
Ce n'est **pas** un biais "Lost in the Middle" classique. C'est un **biais de limite de génération** :
le modèle dépense trop de tokens à raisonner et n'en a plus pour répondre. Augmenter `max_tokens`
fait passer le score de 15% à 75% sans changer le modèle ni le contexte.

**Avec un modèle non-reasoning (Llama 3, GPT-4o) :**

Les performances sont quasi-parfaites sur 40–87 lignes. Le "Lost in the Middle" apparaîtra sur des
contextes beaucoup plus longs (4 000–16 000 tokens, comme étudié dans le papier de Liu et al. 2023).

**Ce que ça enseigne sur les LLMs en production :**

1. **`max_tokens` est un paramètre fonctionnel**, pas cosmétique. Sous-dimensionner ce paramètre
   peut réduire le score de 75% à 0% — sans aucun message d'erreur.

2. **L'architecture reasoning change fondamentalement le profil de coût**. Un modèle reasoning
   nécessite 5–10× plus de tokens de complétion qu'un modèle instruct standard sur la même tâche.

3. **Le biais de position dépend de la longueur du contexte**. Sur 40–87 lignes, il est faible.
   Sur 4 000+ tokens, il devient structurel et documenté scientifiquement.

4. **"Intelligent" ne signifie pas "parfait"**. Un modèle 3B peut passer 100% des cas alignés
   tout en échouant sur tous les cas croisés — selon un pattern très prévisible.

---

## Pour aller plus loin — Pistes et réponses

### `N_LINES = 80` dans `generate_tests.py`
Avec 80 lignes, le biais de position devient plus visible sur les petits modèles. Le score MILIEU
baisse typiquement de 15–30% par rapport au score sur 40 lignes. Le contexte (~560 tokens) approche
la limite de confort des modèles 3B. Les assertions `icontains` du groupe MILIEU commencent à échouer
même avec un bon `max_tokens`.

### Modèle sans reasoning
Avec `llama3-8b-8192` sur Groq (ou tout modèle instruct sans chain-of-thought automatique) :
- Les `[THINK]` disparaissent
- `max_tokens = 50` suffit pour les synthétiques
- `max_tokens = 150` suffit pour les médicaux
- Le score monte à 18–20/20 avec le même jeu de tests

**Comparer les deux profils** (reasoning vs non-reasoning) sur le même jeu de tests est l'expérience
la plus instructive de ce TP.

### Tokens de prompt : synthétiques vs médicaux
- Synthétiques : ~280 tokens de prompt (40 lignes × ~7 tokens/ligne)
- Médicaux : ~650 tokens de prompt (87 lignes, plus denses)

Le ratio est ~2.3×. Pourtant, la difficulté perçue par le modèle est bien supérieure pour les
médicaux — car le document médical a une structure naturelle qui "attire" l'attention du modèle
sur les diagnostics et antécédents, pas nécessairement sur les deux valeurs cibles.

### Papier original "Lost in the Middle" (Liu et al., 2023)
Le papier étudie des contextes de 4 000 à 16 000 tokens avec 10 à 30 documents. Les résultats
montrent une courbe en U : bonnes performances aux extrémités, chute de 30–50% au milieu.
Nos tests sur 40–87 lignes sont à la limite basse de ce phénomène — c'est pourquoi les résultats
sont moins nets, mais le même mécanisme est à l'œuvre.
