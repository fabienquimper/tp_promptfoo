#!/usr/bin/env python3
"""
Télécharge des extraits audio publics connus et génère audio_tests.yaml.

Sources :
  - OpenAI Whisper tests (JFK inauguration, domaine public)
  - HuggingFace Narsil/asr_dummy (MLK 1963, "I know kung fu" Matrix)

Requiert : requests  (pip install requests)
Usage    : python generate_audio_tests.py
"""
import pathlib, sys
import requests
import yaml

ROOT      = pathlib.Path(__file__).parent
AUDIO_DIR = ROOT / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

HEADERS = {"User-Agent": "promptfoo-needle-test/1.0 (educational)"}

HF = "https://huggingface.co/datasets/Narsil/asr_dummy/resolve/main"

AUDIO_SOURCES = [
    {
        "url":        "https://github.com/openai/whisper/raw/main/tests/jfk.flac",
        "filename":   "jfk.flac",
        "transcript": "ask not what your country can do for you ask what you can do for your country",
        "assert":     [{"type": "icontains", "value": "country"}],
        "label":      "JFK inauguration 1961 (OpenAI Whisper)",
    },
    {
        "url":        f"{HF}/mlk.flac",
        "filename":   "mlk.flac",
        "transcript": "i have a dream",
        "assert":     [{"type": "icontains", "value": "dream"}],
        "label":      "MLK 'I have a dream' 1963",
    },
    {
        "url":        f"{HF}/i-know-kung-fu.mp3",
        "filename":   "i-know-kung-fu.mp3",
        "transcript": "i know kung fu",
        "assert":     [{"type": "icontains", "value": "kung"}],
        "label":      "Matrix — 'I know kung fu'",
    },
]


def download(url: str, dest: pathlib.Path) -> bool:
    if dest.exists():
        print(f"  ↩  {dest.name} déjà présent")
        return True
    try:
        print(f"  ↓  {dest.name} …", end=" ", flush=True)
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"OK ({len(r.content) // 1024} KB)")
        return True
    except Exception as e:
        print(f"ERREUR : {e}")
        return False


def main():
    tests = []
    print("Téléchargement des clips audio…\n")

    for src in AUDIO_SOURCES:
        dest = AUDIO_DIR / src["filename"]
        if download(src["url"], dest):
            tests.append({
                "vars": {
                    "audio_file": str(dest.relative_to(ROOT)),
                    "transcript": src["transcript"],
                    "label":      src["label"],
                },
                "assert": src["assert"],
            })
        else:
            print(f"  ⚠  {src['label']} ignoré (échec téléchargement)")

    if not tests:
        print("\n❌  Aucun fichier téléchargé — vérifie ta connexion.")
        sys.exit(1)

    out = ROOT / "audio_tests.yaml"
    out.write_text(yaml.dump(tests, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print(f"\n✓  {len(tests)} tests générés → audio_tests.yaml")
    print("   Lance l'évaluation avec : python eval_audio.py")


if __name__ == "__main__":
    main()
