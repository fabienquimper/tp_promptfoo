#!/usr/bin/env python3
"""
Génère tests.yaml pour l'évaluation Needle-in-a-Haystack de Promptfoo.
Seed fixe = résultats identiques à chaque exécution.

Usage : python generate_tests.py
"""
import random
import yaml

SEED = 42

# Taille du contexte par test.
# 40 lignes ≈ 280 tokens  → modèles avec n_ctx ≥ 512
# 20 lignes ≈ 150 tokens  → modèles contraints (3B locaux, n_ctx = 256)
N_LINES = 40

# 20 scénarios : (nom_cible, position_dans_N_LINES_lignes, groupe)
SCENARIOS = [
    # --- DÉBUT : cible dans les 5 premières lignes (6 tests) ---
    ("ALBATROS",    1, "DÉBUT"),
    ("CYCLONE",     2, "DÉBUT"),
    ("SPHINX",      3, "DÉBUT"),
    ("TORNADE",     4, "DÉBUT"),
    ("METEOR",      5, "DÉBUT"),
    ("FALCON",      2, "DÉBUT"),
    # --- MILIEU : cible entre les lignes 15 et 25 (8 tests) ---
    ("AURORA",     15, "MILIEU"),
    ("ECLIPSE",    17, "MILIEU"),
    ("SOLSTICE",   19, "MILIEU"),
    ("PEGASE",     20, "MILIEU"),
    ("MINERVE",    21, "MILIEU"),
    ("TITAN",      22, "MILIEU"),
    ("ORION",      23, "MILIEU"),
    ("PHOENIX",    25, "MILIEU"),
    # --- FIN : cible dans les 5 dernières lignes (6 tests) ---
    ("TRITON",     36, "FIN"),
    ("NEPTUNE",    37, "FIN"),
    ("SATURNE",    38, "FIN"),
    ("MERCURE",    39, "FIN"),
    ("ANDROMEDE",  40, "FIN"),
    ("CASSIOPEE",  38, "FIN"),
]

# Pool de 80 noms de bruit (étoiles, constellations, mythologie)
NOISE_POOL = [
    "ALCYONE", "BELLATRIX", "CAPELLA", "DENEBOLA", "ELECTRA", "FORNAX",
    "GEMINI", "HYDRA", "INDUS", "JANUS", "KAPPA", "LACERTA", "MIZAR",
    "NORMA", "OCTANS", "PUPPIS", "QUASAR", "RIGEL", "SIRIUS", "TAURUS",
    "URANUS", "VEGA", "XIPHIAS", "ZAURAK", "ACRUX", "CORVUS", "DRACO",
    "ERIDANI", "FURUD", "HAMAL", "IZAR", "KEID", "LUCIDA", "MIMOSA",
    "NAOS", "PHACT", "SABIK", "TEJAT", "VINDEMIATRIX", "WASAT",
    "ADHARA", "BEID", "CELAENO", "DIPHDA", "ENIF", "FOMALHAUT",
    "GIENAH", "HASSALEH", "IKLIL", "JABBAH", "KOCHAB", "LESATH",
    "MARKAB", "NAVI", "PORRIMA", "ROTANEV", "SUALOCIN", "TALITHA",
    "UKDAH", "ZAVIJAVA", "ACRAB", "BOTEIN", "CURSA", "DABIH",
    "ERRAI", "GRAFFIAS", "HEZE", "IMAI", "JISHUI", "KABDHILINAN",
    "LARAWAG", "MAASYM", "NASHIRA", "OKAB", "PRAECIPUA", "RASTABAN",
    "SCHEAT", "TARAZED", "UNUK", "XENOPHON",
]


def gen_id(rng: random.Random) -> str:
    num = rng.randint(1000, 9999)
    letter = rng.choice("ABCDEFGHJKLMNPQRSTVWXYZ")
    suffix = rng.randint(10, 99)
    return f"ID-{num}{letter}-{suffix}"


def build_test(name: str, position: int, group: str,
               rng: random.Random, used_ids: set) -> dict:
    # ID cible unique
    target_id = gen_id(rng)
    while target_id in used_ids:
        target_id = gen_id(rng)
    used_ids.add(target_id)

    n_noise = N_LINES - 1
    noise_names = rng.sample(NOISE_POOL, n_noise)

    noise_ids = []
    for _ in range(n_noise):
        nid = gen_id(rng)
        while nid in used_ids:
            nid = gen_id(rng)
        used_ids.add(nid)
        noise_ids.append(nid)

    lines = []
    noise_idx = 0
    for i in range(1, N_LINES + 1):
        if i == position:
            lines.append(f"{target_id}: {name}")
        else:
            lines.append(f"{noise_ids[noise_idx]}: {noise_names[noise_idx]}")
            noise_idx += 1

    assert_type = "icontains" if group == "MILIEU" else "equals"

    return {
        "description": f"[{group}] Ligne {position}/{N_LINES} — cible : {name} → {target_id}",
        "vars": {
            "target_item": name,
            "context": "\n".join(lines),
        },
        "assert": [
            {"type": assert_type, "value": target_id}
        ],
    }


def main() -> None:
    rng = random.Random(SEED)
    used_ids: set = set()
    tests = []

    for name, position, group in SCENARIOS:
        test = build_test(name, position, group, rng, used_ids)
        tests.append(test)

    # Affichage du récapitulatif
    print(f"{'N°':<4} {'Groupe':<8} {'Pos':>4}  {'Cible':<12}  {'ID attendu'}")
    print("-" * 55)
    for i, (t, (_, pos, grp)) in enumerate(zip(tests, SCENARIOS), 1):
        expected = t["assert"][0]["value"]
        name = t["vars"]["target_item"]
        print(f"{i:<4} {grp:<8} {pos:>4}  {name:<12}  {expected}")

    with open("tests.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            tests,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=200,
        )

    print(f"\n✓  tests.yaml généré avec {len(tests)} tests.")
    print("─" * 55)
    print("Étapes suivantes :")
    print("  1. Edite promptfooconfig.yaml → renseigne LLM_PORT et LLM_MODEL")
    print("  2. docker compose up -d")
    print("  3. docker exec -it promptfoo_local promptfoo eval")
    print("  4. Ouvre http://localhost:15500")


if __name__ == "__main__":
    main()
