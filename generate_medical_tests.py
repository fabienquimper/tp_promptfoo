#!/usr/bin/env python3
"""
Génère medical_tests.yaml — Needle-in-a-Haystack sur compte rendu médical.

Document de base : compte rendu de Mr. Durant (~87 lignes).
Deux aiguilles insérées par test :
  - Groupe sanguin  (position variable)
  - Médicament cible (position variable)

Le LLM doit retrouver les deux valeurs exactes.
Usage : python generate_medical_tests.py
"""
import yaml

# ── Document de base ────────────────────────────────────────────────────────
# ~87 lignes. Zones de position :
#   DÉBUT  : lignes  9–18  (MOTIF DE CONSULTATION + début ANTÉCÉDENTS)
#   MILIEU : lignes 37–65  (ALLERGIES → fin EXAMENS COMPLÉMENTAIRES)
#   FIN    : lignes 72–85  (DIAGNOSTICS + PLAN THÉRAPEUTIQUE)
BASE_LINES = [
    "COMPTE RENDU MÉDICAL — CONFIDENTIEL",
    "Patient : DURANT Jean-Pierre",
    "Date de naissance : 14/03/1962 (63 ans)",
    "Numéro de dossier : 2024-CHU-04471",
    "Date de consultation : 18 novembre 2024",
    "Praticien : Dr. Sophie LEBLANC, MD — Médecine Interne",
    "Établissement : CHU de Bordeaux — Service de Médecine Interne",
    "",
    "MOTIF DE CONSULTATION",
    "Suivi trimestriel pour pathologies chroniques multiples.",
    "Plainte principale : fatigue persistante depuis 6 semaines, dyspnée d'effort modérée.",
    "Pas de douleur thoracique ni de syncope rapportée.",
    "",
    "ANTÉCÉDENTS MÉDICAUX PERSONNELS",
    "Diabète de type 2, diagnostiqué en 2009, suivi en endocrinologie.",
    "Hypertension artérielle essentielle depuis 2011.",
    "Dyslipidémie mixte sous traitement depuis 2013.",
    "Cardiopathie ischémique : IDM antérieur en janvier 2018, stent posé sur IVA proximale.",
    "Insuffisance rénale chronique stade 3a (DFG estimé 52 mL/min/1,73m²).",
    "Hypothyroïdie, diagnostiquée en 2020, substituée.",
    "Obésité de grade 1 (IMC : 31,4 kg/m²).",
    "",
    "ANTÉCÉDENTS CHIRURGICAUX",
    "Appendicectomie en 1985.",
    "Angioplastie coronaire avec pose de stent nu (IVA) en janvier 2018.",
    "Arthroscopie genou droit en 2016.",
    "",
    "ANTÉCÉDENTS FAMILIAUX",
    "Père : décédé d'un IDM à 67 ans.",
    "Mère : diabète de type 2, HTA, décédée à 81 ans d'AVC ischémique.",
    "Frère aîné : dyslipidémie sous traitement.",
    "",
    "ALLERGIES ET INTOLÉRANCES",
    "Pénicilline : allergie documentée (réaction cutanée en 2003).",
    "AINS : intolérance digestive (gastrite médicamenteuse en 2017).",
    "",
    "HABITUDES DE VIE",
    "Tabagisme sevré depuis 2018 (ex-fumeur 20 paquets-années).",
    "Alcool : consommation occasionnelle (1–2 verres/semaine).",
    "Activité physique : marche 30 min/jour depuis rééducation cardiaque.",
    "Régime hypocalorique et hyposodé, suivi par diététicienne.",
    "",
    "EXAMEN CLINIQUE",
    "Poids : 89 kg — Taille : 1,68 m — IMC : 31,5 kg/m²",
    "Pression artérielle : 138/82 mmHg (bras droit, patient assis au repos).",
    "Fréquence cardiaque : 72 bpm, rythme régulier.",
    "Température : 36,7°C — SpO2 : 97% en air ambiant.",
    "Auscultation cardiaque : bruits du cœur réguliers, pas de souffle.",
    "Auscultation pulmonaire : crépitants basaux droits discrets.",
    "Abdomen : souple, indolore, pas d'hépatomégalie.",
    "Membres inférieurs : œdèmes bilatéraux des chevilles (grade 2).",
    "Examen neurologique : sans particularité, GCS 15/15.",
    "",
    "EXAMENS COMPLÉMENTAIRES — Bilan du 10/11/2024",
    "Glycémie à jeun : 7,8 mmol/L (0,95 g/L).",
    "HbA1c : 7,6% (objectif < 7%).",
    "Créatinine : 118 μmol/L — DFG CKD-EPI : 52 mL/min/1,73m².",
    "Natrémie : 138 mmol/L — Kaliémie : 4,1 mmol/L.",
    "Cholestérol total : 4,8 mmol/L — LDL : 2,1 mmol/L — HDL : 0,9 mmol/L.",
    "Triglycérides : 2,3 mmol/L.",
    "TSH : 2,8 mUI/L (valeur normale).",
    "NFS : Hémoglobine 11,8 g/dL — Leucocytes 7,2 G/L — Plaquettes 224 G/L.",
    "Protéinurie des 24h : 0,42 g/24h (microalbuminurie confirmée).",
    "",
    "ECG du 15/11/2024 : rythme sinusal, séquelles d'IDM antérieur (ondes Q V1–V3).",
    "Échocardiographie du 05/11/2024 : FEVG 48%, hypokinésie antérieure séquellaire.",
    "",
    "DIAGNOSTICS RETENUS",
    "1. Diabète de type 2 déséquilibré (HbA1c 7,6%).",
    "2. Hypertension artérielle insuffisamment contrôlée.",
    "3. Dyslipidémie partiellement équilibrée.",
    "4. Insuffisance cardiaque à FEVG légèrement réduite (ICFEr).",
    "5. Insuffisance rénale chronique stade 3a, stable.",
    "6. Hypothyroïdie substituée.",
    "7. Anémie normochrome normocytaire modérée (bilan étiologique en cours).",
    "",
    "PLAN THÉRAPEUTIQUE",
    "Renforcement des mesures hygiéno-diététiques.",
    "Objectif tensionnel : PA < 130/80 mmHg.",
    "Objectif glycémique : HbA1c < 7%.",
    "Bilan martial et ferritine pour explorer l'anémie.",
    "Consultation cardiologique dans 3 mois (réévaluation FEVG).",
    "Consultation néphrologique dans 6 mois (suivi IRC).",
    "Contrôle biologique dans 6 semaines.",
    "",
    "Signature du praticien : Dr. Sophie LEBLANC",
    "Date : 18/11/2024",
]

# ── Pools de valeurs ────────────────────────────────────────────────────────
# (forme complète, forme courte utilisée dans l'assertion)
BLOOD_TYPES = [
    ("O Rh positif (O+)",    "O+"),
    ("A Rh négatif (A-)",    "A-"),
    ("B Rh positif (B+)",    "B+"),
    ("AB Rh négatif (AB-)",  "AB-"),
    ("O Rh négatif (O-)",    "O-"),
    ("A Rh positif (A+)",    "A+"),
    ("B Rh négatif (B-)",    "B-"),
    ("AB Rh positif (AB+)",  "AB+"),
]

MEDICATIONS = [
    "Rosuvastatine 10 mg",
    "Candesartan 16 mg",
    "Dapagliflozine 10 mg",
    "Spironolactone 25 mg",
    "Bisoprolol 5 mg",
    "Lercanidipine 20 mg",
    "Glipizide 5 mg",
    "Empagliflozine 10 mg",
    "Valsartan 160 mg",
    "Carvedilol 12,5 mg",
    "Irbesartan 300 mg",
    "Torasémide 10 mg",
    "Amlodipine 10 mg",
    "Sitagliptine 100 mg",
    "Ézetimibe 10 mg",
    "Allopurinol 300 mg",
    "Gabapentine 300 mg",
    "Rivaroxaban 20 mg",
    "Pantoprazole 40 mg",
    "Colchicine 1 mg",
]

# ── 20 scénarios ─────────────────────────────────────────────────────────────
# (blood_idx, med_idx, blood_pos, med_pos, groupe)
# Les positions sont 1-indexées dans le document de BASE (87 lignes).
# L'aiguille est insérée AVANT la ligne à cette position.
SCENARIOS = [
    # ── DÉBUT / DÉBUT ────────────────────────────────────────────
    (0,  0,  9, 14, "DÉBUT/DÉBUT"),
    (1,  1, 11, 16, "DÉBUT/DÉBUT"),
    (2,  2, 10, 15, "DÉBUT/DÉBUT"),
    (3,  3, 12, 17, "DÉBUT/DÉBUT"),
    # ── MILIEU / MILIEU ──────────────────────────────────────────
    (4,  4, 37, 47, "MILIEU/MILIEU"),
    (5,  5, 40, 52, "MILIEU/MILIEU"),
    (6,  6, 43, 57, "MILIEU/MILIEU"),
    (7,  7, 38, 62, "MILIEU/MILIEU"),
    # ── FIN / FIN ────────────────────────────────────────────────
    (0,  8, 73, 78, "FIN/FIN"),
    (1,  9, 75, 81, "FIN/FIN"),
    (2, 10, 74, 83, "FIN/FIN"),
    (3, 11, 77, 85, "FIN/FIN"),
    # ── DÉBUT (sang) / FIN (méd) — croisé ────────────────────────
    (4, 12, 10, 74, "DÉBUT/FIN"),
    (5, 13, 13, 77, "DÉBUT/FIN"),
    (6, 14,  9, 81, "DÉBUT/FIN"),
    (7, 15, 12, 83, "DÉBUT/FIN"),
    # ── FIN (sang) / DÉBUT (méd) — croisé ────────────────────────
    (0, 16, 74, 11, "FIN/DÉBUT"),
    (1, 17, 77, 14, "FIN/DÉBUT"),
    (2, 18, 72, 10, "FIN/DÉBUT"),
    (3, 19, 80, 13, "FIN/DÉBUT"),
]


def needle_blood(blood_full: str) -> str:
    return f"Groupe sanguin (vérif. pré-op) : {blood_full}"


def needle_med(medication: str) -> str:
    return f"Traitement instauré ce jour : {medication} — 1 cp/j, à réévaluer."


def build_context(base: list[str], blood_line: str, blood_pos: int,
                  med_line: str, med_pos: int) -> str:
    """
    Insère les deux aiguilles dans le document de base.
    blood_pos et med_pos = positions 1-indexées dans le doc de base.
    On insère depuis la position la plus haute pour ne pas décaler les indices.
    """
    lines = list(base)
    for pos, line in sorted([(blood_pos, blood_line), (med_pos, med_line)],
                            key=lambda x: x[0], reverse=True):
        lines.insert(pos - 1, line)
    return "\n".join(lines)


def main() -> None:
    n_base = len(BASE_LINES)
    print(f"Document de base : {n_base} lignes\n")
    print(f"{'N°':<4} {'Groupe':<15} {'Sang (forme courte)':<22} {'pos':>4}  {'Médicament':<22} {'pos':>4}")
    print("─" * 80)

    tests = []
    for i, (b_idx, m_idx, b_pos, m_pos, groupe) in enumerate(SCENARIOS, 1):
        blood_full, blood_short = BLOOD_TYPES[b_idx % len(BLOOD_TYPES)]
        medication = MEDICATIONS[m_idx % len(MEDICATIONS)]

        context = build_context(
            BASE_LINES,
            needle_blood(blood_full), b_pos,
            needle_med(medication),   m_pos,
        )

        tests.append({
            "description": (
                f"[{groupe}] #{i:02d} — "
                f"Sang: {blood_short} (l.{b_pos}) | "
                f"Méd: {medication.split()[0]} (l.{m_pos})"
            ),
            "vars": {
                "context": context,
                "blood_type": blood_full,
                "medication": medication,
            },
            "assert": [
                # blood_short est non-ambigu (ex: "O+", "AB-") → icontains strict
                {"type": "icontains", "value": blood_short},
                # Nom + dosage exact du médicament
                {"type": "icontains", "value": medication},
            ],
        })

        print(
            f"{i:<4} {groupe:<15} {blood_short:<22} {b_pos:>4}  "
            f"{medication:<22} {m_pos:>4}"
        )

    with open("medical_tests.yaml", "w", encoding="utf-8") as f:
        yaml.dump(
            tests,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=500,
        )

    print(f"\n✓  medical_tests.yaml généré ({len(tests)} tests, doc base {n_base} lignes → {n_base + 2} lignes par test).")
    print("─" * 80)
    print("Lancer : docker exec -it promptfoo_local promptfoo eval -c promptfooconfig.medical.yaml")


if __name__ == "__main__":
    main()
