#!/usr/bin/env python3
"""
Génère image_tests.yaml :
  - Photos réelles téléchargées via l'API Wikipedia  → images/real/
  - Documents synthétiques générés avec Pillow        → images/generated/

Utilise les polices système (DejaVu, Liberation, Ubuntu…) — aucun téléchargement de police.

Requiert : pip install pillow requests
Usage    : python generate_image_tests.py
"""
import sys, pathlib, time
import requests
import yaml

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌  Pillow requis : pip install pillow")
    sys.exit(1)

ROOT     = pathlib.Path(__file__).parent
REAL_DIR = ROOT / "images" / "real"
GEN_DIR  = ROOT / "images" / "generated"

for d in [REAL_DIR, GEN_DIR]:
    d.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "promptfoo-needle-test/1.0 (educational)"}

# ── Polices système ────────────────────────────────────────────────────────

_FONT_CANDIDATES = {
    False: [                                               # regular
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ],
    True: [                                                # bold
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
}
_font_cache: dict[tuple, ImageFont.ImageFont] = {}

def fnt(size: int, bold: bool = False) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    for path in _FONT_CANDIDATES[bold]:
        if pathlib.Path(path).exists():
            try:
                f = ImageFont.truetype(path, size)
                _font_cache[key] = f
                return f
            except Exception:
                pass
    try:
        f = ImageFont.load_default(size=size)
    except TypeError:
        f = ImageFont.load_default()
    _font_cache[key] = f
    return f


# ── Images Wikipedia ───────────────────────────────────────────────────────

REAL_SUBJECTS = [
    {
        "wiki":     "Cat",
        "filename": "cat.jpg",
        "question": "What animal is shown in this photo? Reply in one word.",
        "assert":   [{"type": "icontains", "value": "cat"}],
        "label":    "Chat (Wikipedia)",
    },
    {
        "wiki":     "Eiffel_Tower",
        "filename": "eiffel_tower.jpg",
        "question": "What famous landmark is shown in this image? Reply in 1-3 words.",
        "assert":   [{"type": "icontains", "value": "Eiffel"}],
        "label":    "Tour Eiffel (Wikipedia)",
    },
    {
        "wiki":     "Chess",
        "filename": "chess.jpg",
        "question": "What board game is shown in this image? Reply in one word.",
        "assert":   [{"type": "icontains", "value": "chess"}],
        "label":    "Échecs (Wikipedia)",
    },
    {
        "wiki":     "Traffic_light",
        "filename": "traffic_light.jpg",
        "question": "What object or device is shown in this image? Reply in 1-3 words.",
        "assert":   [{"type": "icontains", "value": "traffic"}],
        "label":    "Feu tricolore (Wikipedia)",
    },
]


def fetch_wikipedia_thumbnail(title: str) -> str | None:
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=HEADERS, timeout=10,
        )
        r.raise_for_status()
        # On utilise l'URL telle quelle — Wikipedia CDN n'accepte que des tailles prédéfinies
        return r.json().get("thumbnail", {}).get("source") or None
    except Exception as e:
        print(f"  ⚠  Wikipedia/{title}: {e}")
        return None


def download_file(url: str, dest: pathlib.Path) -> bool:
    if dest.exists():
        print(f"  ↩  {dest.name} déjà présent")
        return True
    try:
        print(f"  ↓  {dest.name} …", end=" ", flush=True)
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"OK ({len(r.content) // 1024} KB)")
        return True
    except Exception as e:
        print(f"ERREUR : {e}")
        return False


# ── Rapport médical ────────────────────────────────────────────────────────

def generate_medical_report(dest: pathlib.Path, blood: str, medication: str,
                             patient: str, dob: str, file_no: str):
    W, H = 800, 480
    img  = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    # En-tête
    draw.rectangle([(0, 0), (W, 65)], fill="#1e4f9c")
    draw.text((20, 12),  "PATIENT MEDICAL REPORT", font=fnt(22, bold=True), fill="white")
    draw.text((545, 22), f"File #: {file_no}",      font=fnt(13),           fill="#c8d8f0")

    def section(y: int, title: str):
        draw.text((20, y), title, font=fnt(13, bold=True), fill="#1e4f9c")
        draw.line([(20, y + 20), (W - 20, y + 20)], fill="#cccccc", width=1)

    def field(y: int, label: str, value: str, highlight: bool = False):
        draw.text((20, y),  f"{label}:", font=fnt(13), fill="#666666")
        draw.text((210, y), value,        font=fnt(13, bold=highlight),
                  fill="#c0392b" if highlight else "#111111")

    section(80,  "PATIENT INFORMATION")
    field(106, "Full Name",     patient)
    field(130, "Date of Birth", dob)
    field(154, "File Number",   file_no)

    section(188, "CLINICAL DATA")
    field(214, "Blood Type", blood,      highlight=True)
    field(238, "Allergies",  "None known")
    field(262, "Weight",     "72 kg")

    section(296, "PRESCRIPTION")
    field(322, "Medication",   medication, highlight=True)
    field(346, "Instructions", "Take as prescribed — do not exceed stated dose")
    field(370, "Next review",  "2024-09-15")

    draw.rectangle([(0, H - 45), (W, H)], fill="#f0f0f5")
    draw.text((20, H - 30),
              "Attending physician: Dr. Leblanc  |  Date: 2024-03-15  |  CONFIDENTIAL",
              font=fnt(11), fill="#999999")

    img.save(dest, quality=95)


# ── Facture ────────────────────────────────────────────────────────────────

def generate_invoice(dest: pathlib.Path, inv_no: str,
                     items: list[tuple[str, int, float]], tax_rate: float):
    W, H = 800, 520
    img  = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (W, 65)], fill="#2c3e50")
    draw.text((20, 12),  "INVOICE",              font=fnt(28, bold=True), fill="white")
    draw.text((510, 14), f"Invoice #: {inv_no}", font=fnt(13),            fill="#bdc3c7")
    draw.text((510, 35), "Date: March 15, 2024", font=fnt(13),            fill="#bdc3c7")

    # En-tête tableau
    y = 85
    draw.rectangle([(20, y), (W - 20, y + 28)], fill="#ecf0f1")
    for x, label in [(30, "Description"), (490, "Qty"), (560, "Unit"), (690, "Total")]:
        draw.text((x, y + 7), label, font=fnt(13, bold=True), fill="#2c3e50")

    y = 120
    subtotal = 0.0
    for desc, qty, unit in items:
        line = qty * unit
        subtotal += line
        draw.text((30,  y), desc,             font=fnt(13), fill="#333333")
        draw.text((495, y), str(qty),          font=fnt(13), fill="#333333")
        draw.text((560, y), f"€{unit:.2f}",    font=fnt(13), fill="#333333")
        draw.text((690, y), f"€{line:.2f}",    font=fnt(13), fill="#333333")
        y += 28

    draw.line([(20, y + 5), (W - 20, y + 5)], fill="#cccccc", width=1)
    y += 22

    tax   = subtotal * tax_rate / 100
    total = subtotal + tax

    for label, amount in [("Subtotal:", subtotal), (f"Tax ({tax_rate:.0f}%):", tax)]:
        draw.text((560, y), label,           font=fnt(13), fill="#666666")
        draw.text((690, y), f"€{amount:.2f}", font=fnt(13), fill="#333333")
        y += 26

    y += 4
    draw.rectangle([(545, y - 6), (W - 20, y + 32)], fill="#2c3e50")
    draw.text((555, y + 4), "TOTAL DUE:",         font=fnt(14, bold=True), fill="white")
    draw.text((675, y + 4), f"€{total:.2f}",      font=fnt(14, bold=True), fill="#f1c40f")

    img.save(dest, quality=95)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    tests = []

    # Photos réelles (Wikipedia)
    print("Téléchargement des images Wikipedia…")
    for subj in REAL_SUBJECTS:
        dest = REAL_DIR / subj["filename"]
        if not dest.exists():
            time.sleep(1)  # courtoisie CDN Wikipedia
        url  = fetch_wikipedia_thumbnail(subj["wiki"])
        if url and download_file(url, dest):
            tests.append({
                "vars": {
                    "image":    str(dest.relative_to(ROOT)),
                    "question": subj["question"],
                    "type":     "photo",
                    "label":    subj["label"],
                },
                "assert": subj["assert"],
            })

    # Documents synthétiques
    print("\nGénération des rapports médicaux…")
    MEDICAL = [
        ("B+",  "Metformin 500mg",   "Dupont Jean",   "15/04/1975", "MED-2024-7832"),
        ("O-",  "Lisinopril 10mg",   "Martin Sophie", "03/09/1988", "MED-2024-4501"),
        ("AB+", "Atorvastatin 20mg", "Bernard Lucas", "22/11/1965", "MED-2024-9120"),
    ]
    for i, (blood, med, name, dob, fno) in enumerate(MEDICAL, 1):
        dest = GEN_DIR / f"medical_{i}.png"
        generate_medical_report(dest, blood, med, name, dob, fno)
        print(f"  ✓  {dest.name}  (blood={blood}, med={med})")

        tests.append({
            "vars": {
                "image":    str(dest.relative_to(ROOT)),
                "question": "What is the patient's blood type shown in this medical report? Reply with the blood type only (e.g. A+).",
                "type":     "document",
                "label":    f"Rapport médical {i} — groupe sanguin ({blood})",
            },
            "assert": [{"type": "icontains", "value": blood}],
        })
        tests.append({
            "vars": {
                "image":    str(dest.relative_to(ROOT)),
                "question": "What medication is prescribed in this medical report? Reply with the drug name only.",
                "type":     "document",
                "label":    f"Rapport médical {i} — médicament ({med.split()[0]})",
            },
            "assert": [{"type": "icontains", "value": med.split()[0]}],
        })

    print("\nGénération des factures…")
    INVOICES: list[tuple[str, list[tuple[str, int, float]], float]] = [
        (
            "INV-2024-042",
            [("Web Design", 1, 2000.0), ("Annual Hosting", 1, 180.0), ("Support (5h)", 5, 85.0)],
            20.0,
        ),
        (
            "INV-2024-089",
            [("Logo Design", 1, 800.0), ("Business Cards", 500, 0.40), ("Branding Guide", 1, 350.0)],
            20.0,
        ),
    ]
    for i, (inv_no, items, tax) in enumerate(INVOICES, 1):
        dest     = GEN_DIR / f"invoice_{i}.png"
        subtotal = sum(q * p for _, q, p in items)
        total    = subtotal * (1 + tax / 100)
        generate_invoice(dest, inv_no, items, tax)
        print(f"  ✓  {dest.name}  (total=€{total:.2f})")

        tests.append({
            "vars": {
                "image":    str(dest.relative_to(ROOT)),
                "question": "What is the total amount due shown in this invoice? Reply with the amount only (e.g. €1234.56).",
                "type":     "document",
                "label":    f"Facture {i} — montant total (€{total:.2f})",
            },
            # On vérifie la partie entière sans virgule de milliers (format €3126.00)
            "assert": [{"type": "icontains", "value": str(int(total))}],
        })

    out = ROOT / "image_tests.yaml"
    out.write_text(yaml.dump(tests, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print(f"\n✓  {len(tests)} tests image générés → image_tests.yaml")
    print("   Lance l'évaluation avec : python eval_image.py")


if __name__ == "__main__":
    main()
