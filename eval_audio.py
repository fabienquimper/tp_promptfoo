#!/usr/bin/env python3
"""
Évalue les tests audio via Groq Whisper (STT).

Requiert :
  - LLM_API_KEY=gsk_... dans .env
  - audio_tests.yaml généré par generate_audio_tests.py

Usage : python eval_audio.py
"""
import os, sys, pathlib, time
import requests
import yaml

ROOT     = pathlib.Path(__file__).parent
ENV_FILE = ROOT / ".env"


def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


load_env()

API_KEY   = os.environ.get("LLM_API_KEY", "")
STT_MODEL = os.environ.get("STT_MODEL", "whisper-large-v3-turbo")
GROQ_BASE = "https://api.groq.com/openai"

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


_MIME = {
    ".wav":  "audio/wav",
    ".flac": "audio/flac",
    ".mp3":  "audio/mpeg",
    ".mp4":  "audio/mp4",
    ".ogg":  "audio/ogg",
    ".m4a":  "audio/mp4",
    ".webm": "audio/webm",
}


def transcribe(audio_path: pathlib.Path) -> str:
    mime = _MIME.get(audio_path.suffix.lower(), "audio/wav")
    with open(audio_path, "rb") as f:
        resp = requests.post(
            f"{GROQ_BASE}/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": (audio_path.name, f, mime)},
            data={"model": STT_MODEL},
            timeout=60,
        )
    resp.raise_for_status()
    return resp.json()["text"].strip()


def check(assertion: dict, output: str) -> bool:
    t, v = assertion["type"], str(assertion["value"])
    if t == "icontains":
        return v.lower() in output.lower()
    if t == "equals":
        return output.strip() == v
    return False


def main():
    if not API_KEY:
        print(f"{RED}❌  LLM_API_KEY manquant dans .env{RESET}")
        sys.exit(1)

    tests_path = ROOT / "audio_tests.yaml"
    if not tests_path.exists():
        print(f"{RED}❌  audio_tests.yaml introuvable{RESET}")
        print("   Lance d'abord : python generate_audio_tests.py")
        sys.exit(1)

    tests = yaml.safe_load(tests_path.read_text(encoding="utf-8"))

    print(f"\n{BOLD}=== Évaluation Audio — Groq Whisper ==={RESET}")
    print(f"Modèle STT : {STT_MODEL}\n")

    passed = failed = 0

    for test in tests:
        v          = test["vars"]
        audio_path = ROOT / v["audio_file"]
        label      = v.get("label", v["audio_file"])
        expected   = v.get("transcript", "")

        print(f"  {label}", end="  …  ", flush=True)

        ok = False
        try:
            transcript = transcribe(audio_path)
            ok = all(check(a, transcript) for a in test["assert"])
            status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            print(status)
            print(f"     attendu  : {expected}")
            print(f"     whisper  : {transcript}")
            if ok:
                passed += 1
            else:
                failed += 1
        except requests.HTTPError as e:
            print(f"{YELLOW}ERREUR HTTP{RESET} {e.response.status_code}: {e.response.text[:100]}")
            failed += 1
        except FileNotFoundError:
            print(f"{YELLOW}ERREUR{RESET} fichier absent : {audio_path}")
            failed += 1

        time.sleep(0.5)

    total = passed + failed
    pct = 100 * passed // total if total else 0
    print(f"\n{BOLD}Score : {passed}/{total}  ({pct}%){RESET}\n")


if __name__ == "__main__":
    main()
