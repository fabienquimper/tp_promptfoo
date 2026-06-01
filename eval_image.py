#!/usr/bin/env python3
"""
Évalue les tests images via un modèle de vision compatible OpenAI (Groq, OpenAI…).

Requiert :
  - LLM_API_KEY dans .env
  - VISION_MODEL dans .env (défaut : meta-llama/llama-4-scout-17b-16e-instruct)
  - image_tests.yaml généré par generate_image_tests.py

Usage : python eval_image.py
"""
import os, sys, base64, pathlib, time
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

API_KEY      = os.environ.get("LLM_API_KEY", "")
BASE_URL     = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai")
VISION_MODEL = os.environ.get("VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}


def image_content_item(image_ref: str) -> dict:
    if image_ref.startswith("http"):
        return {"type": "image_url", "image_url": {"url": image_ref}}
    path = ROOT / image_ref
    mime = MIME.get(path.suffix.lower(), "image/png")
    b64  = base64.b64encode(path.read_bytes()).decode()
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}


def ask_vision(image_ref: str, question: str) -> str:
    resp = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=HEADERS,
        json={
            "model": VISION_MODEL,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": question},
                image_content_item(image_ref),
            ]}],
            "temperature": 0,
            "max_tokens":  200,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


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

    tests_path = ROOT / "image_tests.yaml"
    if not tests_path.exists():
        print(f"{RED}❌  image_tests.yaml introuvable{RESET}")
        print("   Lance d'abord : python generate_image_tests.py")
        sys.exit(1)

    tests = yaml.safe_load(tests_path.read_text(encoding="utf-8"))

    print(f"\n{BOLD}=== Évaluation Images — Vision LLM ==={RESET}")
    print(f"Modèle : {VISION_MODEL}\n")

    by_type: dict[str, dict] = {}
    passed = failed = 0

    for test in tests:
        v     = test["vars"]
        ref   = v["image"]
        q     = v["question"]
        t     = v.get("type", "?")
        label = v.get("label", ref[:45])

        print(f"  [{t:8s}]  {label[:45]}", end="  …  ", flush=True)

        ok = False
        try:
            output = ask_vision(ref, q)
            ok = all(check(a, output) for a in test["assert"])
            status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            print(f"{status}  → {output[:60]}")
            if ok:
                passed += 1
            else:
                failed += 1
        except requests.HTTPError as e:
            print(f"{YELLOW}ERREUR HTTP{RESET} {e.response.status_code}: {e.response.text[:100]}")
            failed += 1
        except FileNotFoundError as e:
            print(f"{YELLOW}ERREUR{RESET} fichier manquant : {e}")
            failed += 1

        by_type.setdefault(t, {"pass": 0, "fail": 0})
        by_type[t]["pass" if ok else "fail"] += 1
        time.sleep(3)

    total = passed + failed
    pct = 100 * passed // total if total else 0
    print(f"\n{BOLD}Score : {passed}/{total}  ({pct}%){RESET}")
    for tp, r in sorted(by_type.items()):
        n = r["pass"] + r["fail"]
        print(f"  {tp:12s} : {r['pass']}/{n}  {'✓' * r['pass']}{'✗' * r['fail']}")
    print()


if __name__ == "__main__":
    main()
