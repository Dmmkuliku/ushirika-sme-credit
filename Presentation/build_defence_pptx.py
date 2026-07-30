"""
Ushirika / Group 15 defence presentation — tuned for a 5-minute talk by 5 speakers.
~7 slides. Each speaker owns ~1 minute. Keep wording short so slides support speech.
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parent / "Ushirika_Group15_Defence_Presentation.pptx"
OUT_ALT = Path(__file__).resolve().parent / "Ushirika_Group15_Defence_v13.pptx"
OUT_SEM2 = Path(r"C:\Users\USER\OneDrive\Desktop\SEM 2\Data Science Project\Ushirika_Group15.pptx")

FOREST = RGBColor(0x0B, 0x3D, 0x2E)
FOREST_DEEP = RGBColor(0x06, 0x28, 0x20)
LAGOON = RGBColor(0x1A, 0x7A, 0x6D)
LAGOON_BRIGHT = RGBColor(0x23, 0x96, 0x88)
MIST = RGBColor(0xE6, 0xEE, 0xF0)
PAPER = RGBColor(0xF4, 0xF8, 0xF9)
INK = RGBColor(0x0F, 0x28, 0x30)
MUTED = RGBColor(0x4A, 0x5E, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
SUCCESS = RGBColor(0x1A, 0x6B, 0x45)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
TOTAL = 7

# Speaking order (~60s each after a short group open)
SPEAKERS = [
    "Herman Edward Mkumbwa",
    "Raymond Elphance Tungaraza",
    "Edwin Celestin Silayo",
    "Grace Joachim Mohammed",
    "Priscila Nestor Mpembela",
]


def fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def rect(slide, left, top, width, height, color):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    fill(s, color)
    return s


def round_rect(slide, left, top, width, height, color):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    fill(s, color)
    try:
        s.adjustments[0] = 0.08
    except Exception:
        pass
    return s


def set_run(run, text, size=16, bold=False, color=INK, font="Calibri"):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def textbox(slide, left, top, width, height, text, size=16, bold=False, color=INK, align=PP_ALIGN.LEFT, font="Calibri"):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    lines = text.split("\n") if text is not None else [""]
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(3)
        run = p.add_run()
        set_run(run, line, size, bold, color, font)
    return box


def bullets(slide, left, top, width, height, items, size=14, color=INK):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_before = Pt(4)
        p.space_after = Pt(4)
        run = p.add_run()
        set_run(run, f"•  {item}", size, False, color)
    return box


def footer(slide, page):
    rect(slide, Inches(0), Inches(7.15), SLIDE_W, Inches(0.35), FOREST_DEEP)
    textbox(
        slide,
        Inches(0.45),
        Inches(7.18),
        Inches(10),
        Inches(0.28),
        "USHIRIKA — 5-MINUTE DEFENCE  ·  GROUP 15",
        size=10,
        color=RGBColor(0xB8, 0xD0, 0xC8),
    )
    textbox(
        slide,
        Inches(11.4),
        Inches(7.18),
        Inches(1.5),
        Inches(0.28),
        f"{page}  /  {TOTAL}",
        size=10,
        color=RGBColor(0xB8, 0xD0, 0xC8),
        align=PP_ALIGN.RIGHT,
    )


def bg(slide, color=PAPER):
    rect(slide, Inches(0), Inches(0), SLIDE_W, SLIDE_H, color)


def section_header(slide, kicker, title, subtitle=None):
    textbox(slide, Inches(0.55), Inches(0.28), Inches(12), Inches(0.28), kicker, size=12, bold=True, color=LAGOON)
    rect(slide, Inches(0.55), Inches(0.62), Inches(0.1), Inches(0.48), LAGOON_BRIGHT)
    textbox(
        slide,
        Inches(0.8),
        Inches(0.55),
        Inches(11.8),
        Inches(0.5),
        title,
        size=24,
        bold=True,
        color=FOREST,
        font="Georgia",
    )
    if subtitle:
        textbox(slide, Inches(0.55), Inches(1.15), Inches(12.2), Inches(0.35), subtitle, size=13, color=MUTED)


def metric(slide, left, top, w, h, value, label, accent=LAGOON):
    round_rect(slide, left, top, w, h, WHITE)
    rect(slide, left, top, Inches(0.1), h, accent)
    textbox(slide, left + Inches(0.25), top + Inches(0.22), w - Inches(0.35), Inches(0.4), value, size=22, bold=True, color=FOREST)
    textbox(slide, left + Inches(0.25), top + Inches(0.7), w - Inches(0.35), Inches(0.45), label, size=11, color=MUTED)


def speaker_chip(slide, speaker_no, name, timing):
    """Visible cue so each person knows when they speak."""
    round_rect(slide, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.45), FOREST)
    textbox(
        slide,
        Inches(0.7),
        Inches(6.6),
        Inches(11.9),
        Inches(0.35),
        f"SPEAKER {speaker_no}: {name}   ·   ~{timing}",
        size=12,
        bold=True,
        color=WHITE,
    )


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # 1 Title + speaking plan (~40s open)
    s = prs.slides.add_slide(blank)
    bg(s, FOREST_DEEP)
    rect(s, Inches(0), Inches(0), Inches(0.35), SLIDE_H, LAGOON)
    textbox(
        s,
        Inches(0.8),
        Inches(0.45),
        Inches(11.5),
        Inches(0.3),
        "EASTERN AFRICA STATISTICAL TRAINING CENTRE  ·  5-MINUTE DEFENCE",
        size=12,
        bold=True,
        color=LAGOON_BRIGHT,
    )
    textbox(
        s,
        Inches(0.8),
        Inches(0.95),
        Inches(11.5),
        Inches(1.15),
        "ML Credit Risk Assessment for\nSME Value Chain Financing — Tanzania",
        size=28,
        bold=True,
        color=WHITE,
        font="Georgia",
    )
    textbox(
        s,
        Inches(0.8),
        Inches(2.25),
        Inches(11.5),
        Inches(0.35),
        "Platform: Ushirika  ·  Supervisor: Mr. Rajabu Msangi  ·  BSc Data Science III · 2025/2026",
        size=14,
        color=MIST,
    )
    textbox(s, Inches(0.8), Inches(2.85), Inches(11.5), Inches(0.3), "SPEAKING ORDER (≈1 minute each)", size=13, bold=True, color=LAGOON_BRIGHT)
    for i, name in enumerate(SPEAKERS):
        top = Inches(3.25 + i * 0.48)
        round_rect(s, Inches(0.8), top, Inches(11.5), Inches(0.42), RGBColor(0x0D, 0x45, 0x36))
        textbox(s, Inches(1.0), top + Inches(0.05), Inches(1.2), Inches(0.3), f"S{i + 1}", size=14, bold=True, color=LAGOON_BRIGHT)
        textbox(s, Inches(2.2), top + Inches(0.05), Inches(9.8), Inches(0.3), name, size=14, color=WHITE)
    textbox(
        s,
        Inches(0.8),
        Inches(6.7),
        Inches(11.5),
        Inches(0.3),
        "Live: ushirika-sme-portal.vercel.app",
        size=12,
        color=RGBColor(0x9B, 0xC4, 0xBA),
    )
    textbox(s, Inches(11.4), Inches(6.7), Inches(1.5), Inches(0.3), "1  /  7", size=11, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)

    # 2 Speaker 1 — Problem
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(
        s,
        "SPEAKER 1 · PROBLEM  ·  ~55s",
        "Why fair SME credit is still hard in Tanzania",
        "Say the problem in one clear minute — then hand over.",
    )
    cards = [
        ("01", "Collateral barrier", "Banks ask for collateral and formal books most SMEs do not have."),
        ("02", "Old risk tools", "Static ratios miss viable traders in informal supply chains."),
        ("03", "Unused payment data", "Buyer–supplier payment behaviour is rich risk data, unused today."),
        ("04", "Our answer", "Ushirika scores SMEs from real transactions — not collateral alone."),
    ]
    for i, (num, title, body) in enumerate(cards):
        left = Inches(0.5 + (i % 2) * 6.35)
        top = Inches(1.7 + (i // 2) * 2.15)
        round_rect(s, left, top, Inches(6.05), Inches(1.95), WHITE)
        rect(s, left, top, Inches(0.12), Inches(1.95), LAGOON if i % 2 == 0 else FOREST)
        textbox(s, left + Inches(0.4), top + Inches(0.25), Inches(1), Inches(0.35), num, size=18, bold=True, color=LAGOON)
        textbox(s, left + Inches(1.2), top + Inches(0.28), Inches(4.5), Inches(0.35), title, size=16, bold=True, color=FOREST)
        textbox(s, left + Inches(0.4), top + Inches(0.85), Inches(5.3), Inches(0.85), body, size=14, color=MUTED)
    speaker_chip(s, 1, SPEAKERS[0], "55 seconds")
    footer(s, 2)

    # 3 Speaker 2 — Aim & what we built
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(
        s,
        "SPEAKER 2 · AIM & SOLUTION  ·  ~55s",
        "What we built: Ushirika",
        "State the aim, then the live product in three breaths.",
    )
    round_rect(s, Inches(0.5), Inches(1.65), Inches(12.3), Inches(1.2), WHITE)
    textbox(s, Inches(0.75), Inches(1.78), Inches(11.8), Inches(0.25), "GENERAL AIM", size=11, bold=True, color=LAGOON)
    textbox(
        s,
        Inches(0.75),
        Inches(2.1),
        Inches(11.8),
        Inches(0.55),
        "An automated platform that uses supply-chain transactions and machine learning to give inclusive SME credit scores in Tanzania.",
        size=15,
        color=INK,
    )
    layers = [
        ("Portal", "SME · Lender · Admin\nEnglish / Kiswahili"),
        ("API", "Secure FastAPI\nJWT · rate limits"),
        ("ML", "Random Forest\nplain-language signals"),
        ("Safety", "PII protected\nconservative loans"),
    ]
    for i, (t, d) in enumerate(layers):
        left = Inches(0.5 + i * 3.2)
        round_rect(s, left, Inches(3.15), Inches(3.0), Inches(2.9), WHITE)
        rect(s, left, Inches(3.15), Inches(3.0), Inches(0.55), FOREST if i % 2 else LAGOON)
        textbox(s, left + Inches(0.15), Inches(3.25), Inches(2.7), Inches(0.35), t, size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, left + Inches(0.25), Inches(3.95), Inches(2.5), Inches(1.8), d, size=14, color=INK, align=PP_ALIGN.CENTER)
    speaker_chip(s, 2, SPEAKERS[1], "55 seconds")
    footer(s, 3)

    # 4 Speaker 3 — Method
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(
        s,
        "SPEAKER 3 · METHOD  ·  ~55s",
        "How we trained and tested fairly",
        "Keep this technical but short — protocol, then two models.",
    )
    round_rect(s, Inches(0.5), Inches(1.65), Inches(6.1), Inches(4.5), WHITE)
    textbox(s, Inches(0.75), Inches(1.85), Inches(5.6), Inches(0.35), "PROTOCOL", size=14, bold=True, color=LAGOON)
    bullets(
        s,
        Inches(0.75),
        Inches(2.35),
        Inches(5.6),
        Inches(3.5),
        [
            "Features from payments, delays, volume, partners.",
            "80/20 stratified train–test split (seed 42).",
            "Train models only on training data.",
            "Report hold-out Accuracy, Precision, Recall, F1, ROC-AUC.",
            "Score only after ≥5 SME transactions.",
        ],
        size=14,
    )
    round_rect(s, Inches(6.9), Inches(1.65), Inches(5.9), Inches(4.5), WHITE)
    textbox(s, Inches(7.15), Inches(1.85), Inches(5.4), Inches(0.35), "TWO MODELS", size=14, bold=True, color=LAGOON)
    bullets(
        s,
        Inches(7.15),
        Inches(2.35),
        Inches(5.4),
        Inches(3.5),
        [
            "Baseline: Logistic Regression.",
            "Primary: Random Forest (ensemble).",
            "Choose by hold-out ROC-AUC.",
            "Score range ~300–850 · Low ≥650 · Medium 500–649 · High <500.",
            "Large one-off deals do not inflate loan size.",
        ],
        size=14,
    )
    speaker_chip(s, 3, SPEAKERS[2], "55 seconds")
    footer(s, 4)

    # 5 Speaker 4 — Findings
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(
        s,
        "SPEAKER 4 · FINDINGS  ·  ~60s",
        "Random Forest is the stronger model",
        "Lead with the headline numbers, then one interpretation sentence.",
    )
    metric(s, Inches(0.5), Inches(1.7), Inches(3.0), Inches(1.4), "95.8%", "RF ROC-AUC", SUCCESS)
    metric(s, Inches(3.7), Inches(1.7), Inches(3.0), Inches(1.4), "88.6%", "RF Accuracy", LAGOON)
    metric(s, Inches(6.9), Inches(1.7), Inches(3.0), Inches(1.4), "87.5%", "LR ROC-AUC", RGBColor(0x8A, 0x5A, 0x00))
    metric(s, Inches(10.1), Inches(1.7), Inches(2.7), Inches(1.4), "RF wins", "Selected primary", FOREST)
    round_rect(s, Inches(0.5), Inches(3.4), Inches(12.3), Inches(2.7), WHITE)
    textbox(s, Inches(0.8), Inches(3.6), Inches(11.7), Inches(0.35), "Hold-out test (unseen data)", size=14, bold=True, color=FOREST)
    bullets(
        s,
        Inches(0.8),
        Inches(4.1),
        Inches(11.7),
        Inches(1.8),
        [
            "RF: Precision 93.0% · Recall 85.7% · F1 89.2%.",
            "LR: Precision 75.8% · Recall 87.7% · F1 81.3%.",
            "Plain signals users see: on-time payments, failed payments, late days, trading volume, sales trend.",
            "Conclusion: ensemble learning beat classical regression on this task.",
        ],
        size=14,
    )
    speaker_chip(s, 4, SPEAKERS[3], "60 seconds")
    footer(s, 5)

    # 6 Speaker 5 — Objectives met + limits
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(
        s,
        "SPEAKER 5 · RESULTS & CLOSE  ·  ~55s",
        "Aim met — and what comes next",
        "Confirm the three objectives, name one limit, invite questions.",
    )
    rows = [
        ("1", "Features ready", "Transactions → clear behavioural predictors."),
        ("2", "RF vs LR", "RF wins on ROC-AUC (95.8% vs 87.5%)."),
        ("3", "Validated", "Accuracy, Precision, Recall, F1, ROC-AUC reported."),
    ]
    for i, (num, title, body) in enumerate(rows):
        left = Inches(0.5 + i * 4.2)
        round_rect(s, left, Inches(1.7), Inches(4.0), Inches(2.35), WHITE)
        rect(s, left, Inches(1.7), Inches(4.0), Inches(0.55), FOREST if i != 1 else LAGOON)
        textbox(s, left + Inches(0.2), Inches(1.8), Inches(3.6), Inches(0.35), f"{num}  {title}", size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, left + Inches(0.3), Inches(2.5), Inches(3.4), Inches(1.2), body, size=14, color=INK, align=PP_ALIGN.CENTER)
    round_rect(s, Inches(0.5), Inches(4.3), Inches(12.3), Inches(1.8), FOREST)
    textbox(s, Inches(0.75), Inches(4.5), Inches(11.8), Inches(0.3), "ONE LIMIT + ONE ASK", size=13, bold=True, color=LAGOON_BRIGHT)
    textbox(
        s,
        Inches(0.75),
        Inches(4.95),
        Inches(11.8),
        Inches(0.9),
        "Prototype is live, but not a bank-production system yet. Next: pilot with partner lenders on real SME ledgers, then strengthen identity checks and database hosting.",
        size=14,
        color=WHITE,
    )
    speaker_chip(s, 5, SPEAKERS[4], "55 seconds")
    footer(s, 6)

    # 7 Thank you
    s = prs.slides.add_slide(blank)
    bg(s, FOREST_DEEP)
    rect(s, Inches(0), Inches(0), Inches(0.35), SLIDE_H, LAGOON_BRIGHT)
    textbox(s, Inches(0.8), Inches(1.6), Inches(11.5), Inches(0.35), "GROUP 15", size=14, bold=True, color=LAGOON_BRIGHT)
    textbox(s, Inches(0.8), Inches(2.15), Inches(11.5), Inches(0.8), "Asanteni", size=40, bold=True, color=WHITE, font="Georgia")
    textbox(
        s,
        Inches(0.8),
        Inches(3.2),
        Inches(11.5),
        Inches(0.6),
        "Questions and discussion",
        size=20,
        color=MIST,
    )
    textbox(
        s,
        Inches(0.8),
        Inches(4.2),
        Inches(11.5),
        Inches(1.5),
        "\n".join(SPEAKERS) + "\n\nSupervisor: Mr. Rajabu Msangi",
        size=14,
        color=RGBColor(0xB8, 0xD0, 0xC8),
    )
    textbox(
        s,
        Inches(0.8),
        Inches(6.5),
        Inches(11.5),
        Inches(0.35),
        "ushirika-sme-portal.vercel.app",
        size=14,
        bold=True,
        color=LAGOON_BRIGHT,
    )
    textbox(s, Inches(11.4), Inches(6.5), Inches(1.5), Inches(0.35), "7  /  7", size=12, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)

    saved = []
    for path in (OUT, OUT_SEM2):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(path))
            saved.append(str(path))
            print(f"Saved: {path}")
        except PermissionError:
            if path == OUT:
                prs.save(str(OUT_ALT))
                saved.append(str(OUT_ALT))
                print(f"Original PPT locked; saved: {OUT_ALT}")
            else:
                print(f"Could not write {path} (file open?) — close PowerPoint and re-run.")
    return saved


if __name__ == "__main__":
    build()
