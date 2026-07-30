"""
Ushirika / Group 15 defence presentation (9 slides).
Same story as before — title → background → aim → what was built →
literature → method → findings → results → close — just tighter.
No speaker names or timing labels on slides.
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
TOTAL = 9


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
        "USHIRIKA — SME VALUE CHAIN CREDIT RISK",
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
        size=26,
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


def met_badge(slide, left, top):
    round_rect(slide, left, top, Inches(0.85), Inches(0.32), SUCCESS)
    textbox(slide, left, top + Inches(0.02), Inches(0.85), Inches(0.28), "MET", size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    # 1 Title
    s = prs.slides.add_slide(blank)
    bg(s, FOREST_DEEP)
    rect(s, Inches(0), Inches(0), Inches(0.35), SLIDE_H, LAGOON)
    textbox(
        s,
        Inches(0.8),
        Inches(0.7),
        Inches(11.5),
        Inches(0.35),
        "EASTERN AFRICA STATISTICAL TRAINING CENTRE  ·  CAPSTONE PROJECT DEFENCE",
        size=12,
        bold=True,
        color=LAGOON_BRIGHT,
    )
    textbox(
        s,
        Inches(0.8),
        Inches(1.25),
        Inches(11.5),
        Inches(1.3),
        "Development of a Machine Learning-Based\nCredit Risk Assessment Model for SME\nValue Chain Financing",
        size=28,
        bold=True,
        color=WHITE,
        font="Georgia",
    )
    textbox(
        s,
        Inches(0.8),
        Inches(2.75),
        Inches(11.5),
        Inches(0.4),
        "A Case Study of Tanzania’s Supply Chains  ·  Platform: Ushirika",
        size=16,
        color=MIST,
    )
    textbox(
        s,
        Inches(0.8),
        Inches(3.4),
        Inches(11.5),
        Inches(1.0),
        "Group 15  ·  Bachelor of Data Science (Year III)\n"
        "Academic Year 2025/2026",
        size=14,
        color=RGBColor(0xB8, 0xD0, 0xC8),
    )
    textbox(
        s,
        Inches(0.8),
        Inches(6.7),
        Inches(10),
        Inches(0.3),
        "Live portal: ushirika-sme-portal.vercel.app",
        size=11,
        color=RGBColor(0x9B, 0xC4, 0xBA),
    )
    textbox(s, Inches(11.4), Inches(6.7), Inches(1.5), Inches(0.3), "1  /  9", size=11, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)

    # 2 Background
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "BACKGROUND", "Why Tanzanian SMEs still struggle to get fair credit")
    cards = [
        ("01", "Collateral-heavy credit", "Banks still rely on collateral and formal statements that most Tanzanian SMEs do not have."),
        ("02", "Static risk metrics", "Old ratios often miss viable businesses that work in informal or semi-formal supply chains."),
        ("03", "Unused transaction signals", "How buyers and suppliers actually pay is strong risk data — but few systems use it."),
        ("04", "Missing-middle gap", "Without another way to score them, good SMEs stay locked out of formal finance."),
    ]
    for i, (num, title, body) in enumerate(cards):
        left = Inches(0.5 + (i % 2) * 6.35)
        top = Inches(1.7 + (i // 2) * 2.4)
        round_rect(s, left, top, Inches(6.05), Inches(2.15), WHITE)
        rect(s, left, top, Inches(0.12), Inches(2.15), LAGOON if i % 2 == 0 else FOREST)
        textbox(s, left + Inches(0.4), top + Inches(0.3), Inches(1), Inches(0.35), num, size=18, bold=True, color=LAGOON)
        textbox(s, left + Inches(1.2), top + Inches(0.3), Inches(4.5), Inches(0.35), title, size=16, bold=True, color=FOREST)
        textbox(s, left + Inches(0.4), top + Inches(0.85), Inches(5.3), Inches(1.0), body, size=13, color=MUTED)
    footer(s, 2)

    # 3 Aim
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "AIM OF THE PROJECT", "What we set out to build")
    round_rect(s, Inches(0.5), Inches(1.65), Inches(12.3), Inches(1.35), WHITE)
    textbox(s, Inches(0.75), Inches(1.8), Inches(11.8), Inches(0.3), "GENERAL OBJECTIVE", size=11, bold=True, color=LAGOON)
    textbox(
        s,
        Inches(0.75),
        Inches(2.15),
        Inches(11.8),
        Inches(0.7),
        "Build a working platform that reads supply-chain transactions and uses machine learning to give fairer, more accurate credit risk scores for Tanzanian SMEs.",
        size=14,
        color=INK,
    )
    objs = [
        ("01", "Preprocessing & features", "Convert raw supply-chain transactions into useful predictors."),
        ("02", "Compare ML vs classical", "Evaluate Random Forest against Logistic Regression."),
        ("03", "Validate with metrics", "Assess reliability using Accuracy, Precision, Recall, F1 and ROC-AUC."),
    ]
    for i, (num, title, body) in enumerate(objs):
        left = Inches(0.5 + i * 4.2)
        round_rect(s, left, Inches(3.3), Inches(4.0), Inches(3.1), WHITE)
        rect(s, left, Inches(3.3), Inches(4.0), Inches(0.65), FOREST if i != 1 else LAGOON)
        textbox(s, left + Inches(0.2), Inches(3.42), Inches(3.6), Inches(0.4), num + "  " + title, size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, left + Inches(0.3), Inches(4.2), Inches(3.4), Inches(1.8), body, size=13, color=INK)
    footer(s, 3)

    # 4 What was built
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "WHAT WAS BUILT", "Ushirika — a working credit platform for SMEs and lenders")
    layers = [
        ("Frontend", "Vite portal\nSME · Lender · Admin\nEnglish / Kiswahili", LAGOON),
        ("API", "FastAPI + JWT\nSecure auth flows\nRole-based access", FOREST),
        ("ML Core", "Feature engineering\nRF (primary) + LR\nPlain repayment signals", LAGOON_BRIGHT),
        ("Data & Ethics", "SQL storage\nPII protected\nConservative loan caps", FOREST_DEEP),
    ]
    for i, (t, d, c) in enumerate(layers):
        left = Inches(0.45 + i * 3.2)
        round_rect(s, left, Inches(1.75), Inches(3.0), Inches(3.5), WHITE)
        rect(s, left, Inches(1.75), Inches(3.0), Inches(0.6), c)
        textbox(s, left + Inches(0.15), Inches(1.88), Inches(2.7), Inches(0.35), t, size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, left + Inches(0.25), Inches(2.6), Inches(2.5), Inches(2.3), d, size=13, color=INK, align=PP_ALIGN.CENTER)
        if i < 3:
            textbox(s, left + Inches(2.85), Inches(3.2), Inches(0.4), Inches(0.35), "→", size=20, bold=True, color=LAGOON, align=PP_ALIGN.CENTER)
    textbox(
        s,
        Inches(0.55),
        Inches(5.55),
        Inches(12.2),
        Inches(1.2),
        "Lenders can search an SME, open the profile, and see score, risk band, plain signals and history.\n"
        "Registration checks NIDA against date of birth, and uses region and district lists in English or Kiswahili.\n"
        "The portal works on desktop and on phone.",
        size=13,
        color=MUTED,
    )
    footer(s, 4)

    # 5 Literature + gap
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "LITERATURE REVIEW", "What the literature establishes, and what it leaves out")
    cites = [
        ("Breiman (2001)", "Random Forests capture non-linear patterns better than single models."),
        ("Lessmann et al. (2015)", "Ensemble classifiers outperform classical baselines in credit scoring."),
        ("Khandani et al. (2010)", "Transactional data can proxy creditworthiness where statements are thin."),
        ("Klapper (2006)", "Value-chain financing uses buyer–supplier links instead of collateral alone."),
    ]
    for i, (a, b) in enumerate(cites):
        top = Inches(1.65 + i * 0.85)
        round_rect(s, Inches(0.5), top, Inches(7.4), Inches(0.75), WHITE)
        textbox(s, Inches(0.7), top + Inches(0.12), Inches(7.0), Inches(0.25), a, size=13, bold=True, color=FOREST)
        textbox(s, Inches(0.7), top + Inches(0.4), Inches(7.0), Inches(0.3), b, size=12, color=MUTED)
    round_rect(s, Inches(8.2), Inches(1.65), Inches(4.6), Inches(4.7), FOREST)
    textbox(s, Inches(8.45), Inches(1.9), Inches(4.1), Inches(0.35), "THE GAP (TZ context)", size=14, bold=True, color=LAGOON_BRIGHT)
    bullets(
        s,
        Inches(8.45),
        Inches(2.45),
        Inches(4.1),
        Inches(3.6),
        [
            "Few platforms join live SME transactions with ML scoring.",
            "Most benchmarks use developed-market data.",
            "Supply-chain signals remain under-used locally.",
            "Ushirika turns that gap into a working prototype.",
        ],
        size=13,
        color=WHITE,
    )
    footer(s, 5)

    # 6 Method
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "EVALUATION METHOD", "How we trained and tested the models")
    round_rect(s, Inches(0.5), Inches(1.65), Inches(6.1), Inches(4.7), WHITE)
    textbox(s, Inches(0.75), Inches(1.85), Inches(5.6), Inches(0.35), "TRAINING PROTOCOL", size=14, bold=True, color=LAGOON)
    bullets(
        s,
        Inches(0.75),
        Inches(2.35),
        Inches(5.6),
        Inches(3.7),
        [
            "Features from payment behaviour, volume, delays and partners.",
            "80/20 stratified train–test split (seed 42).",
            "Models fit on training data only; GridSearchCV uses ROC-AUC.",
            "Hold-out metrics: Accuracy, Precision, Recall, F1, ROC-AUC.",
            "An SME is scored only after at least five transactions.",
            "Rare large deals are down-weighted so they do not inflate loan size.",
        ],
        size=13,
    )
    round_rect(s, Inches(6.9), Inches(1.65), Inches(5.9), Inches(4.7), WHITE)
    textbox(s, Inches(7.15), Inches(1.85), Inches(5.4), Inches(0.35), "TWO MODELS COMPARED", size=14, bold=True, color=LAGOON)
    bullets(
        s,
        Inches(7.15),
        Inches(2.35),
        Inches(5.4),
        Inches(3.7),
        [
            "Baseline: Logistic Regression with scaling.",
            "Primary: Random Forest Classifier.",
            "Selection metric: hold-out ROC-AUC.",
            "Score range about 300–850.",
            "Risk bands: Low ≥650 · Medium 500–649 · High <500.",
            "Users see plain signals such as on-time payments and late days.",
        ],
        size=13,
    )
    footer(s, 6)

    # 7 Findings (features + metrics combined)
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "FINDINGS", "Random Forest outperformed Logistic Regression on unseen test data")
    metric(s, Inches(0.5), Inches(1.65), Inches(3.0), Inches(1.3), "95.8%", "RF ROC-AUC", SUCCESS)
    metric(s, Inches(3.7), Inches(1.65), Inches(3.0), Inches(1.3), "88.6%", "RF Accuracy", LAGOON)
    metric(s, Inches(6.9), Inches(1.65), Inches(3.0), Inches(1.3), "87.5%", "LR ROC-AUC", RGBColor(0x8A, 0x5A, 0x00))
    metric(s, Inches(10.1), Inches(1.65), Inches(2.7), Inches(1.3), "RF wins", "Primary model", FOREST)
    round_rect(s, Inches(0.5), Inches(3.2), Inches(12.3), Inches(3.3), WHITE)
    textbox(s, Inches(0.8), Inches(3.4), Inches(11.7), Inches(0.35), "What the numbers mean", size=14, bold=True, color=FOREST)
    bullets(
        s,
        Inches(0.8),
        Inches(3.9),
        Inches(11.7),
        Inches(2.4),
        [
            "RF: Precision 93.0% · Recall 85.7% · F1 89.2%.",
            "LR: Precision 75.8% · Recall 87.7% · F1 81.3%.",
            "Useful predictors include payment reliability, delay, trading volume, partner mix and sales trend.",
            "That is why Random Forest is the scoring model in the live prototype.",
        ],
        size=14,
    )
    footer(s, 7)

    # 8 Results against aim + discussion
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "RESULTS AGAINST AIM", "Objectives met — with clear limits still ahead")
    rows = [
        ("1", "Preprocessing & features", "Transactions become behavioural predictors used for scoring."),
        ("2", "Ensemble vs classical", "RF beats LR on ROC-AUC (95.8% vs 87.5%)."),
        ("3", "Standard evaluation", "Accuracy, Precision, Recall, F1 and ROC-AUC guide model choice."),
    ]
    for i, (num, title, body) in enumerate(rows):
        top = Inches(1.6 + i * 1.15)
        round_rect(s, Inches(0.5), top, Inches(12.3), Inches(1.05), WHITE)
        rect(s, Inches(0.5), top, Inches(0.7), Inches(1.05), FOREST if i != 1 else LAGOON)
        textbox(s, Inches(0.55), top + Inches(0.3), Inches(0.6), Inches(0.4), num, size=20, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, Inches(1.5), top + Inches(0.18), Inches(9.5), Inches(0.3), title, size=15, bold=True, color=FOREST)
        textbox(s, Inches(1.5), top + Inches(0.55), Inches(9.5), Inches(0.4), body, size=13, color=MUTED)
        met_badge(s, Inches(11.6), top + Inches(0.35))
    round_rect(s, Inches(0.5), Inches(5.2), Inches(12.3), Inches(1.55), FOREST)
    textbox(s, Inches(0.75), Inches(5.35), Inches(11.8), Inches(0.3), "LIMITS & NEXT STEPS", size=12, bold=True, color=LAGOON_BRIGHT)
    textbox(
        s,
        Inches(0.75),
        Inches(5.75),
        Inches(11.8),
        Inches(0.8),
        "The portal is live, but it is still a prototype — not a bank production system. Next we need a lender pilot on real SME ledgers, then stronger identity checks, hosting and ongoing model review.",
        size=13,
        color=WHITE,
    )
    footer(s, 8)

    # 9 Conclusion
    s = prs.slides.add_slide(blank)
    bg(s, FOREST_DEEP)
    rect(s, Inches(0), Inches(0), Inches(0.35), SLIDE_H, LAGOON_BRIGHT)
    textbox(s, Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.3), "CONCLUSION", size=12, bold=True, color=LAGOON_BRIGHT)
    textbox(
        s,
        Inches(0.8),
        Inches(1.2),
        Inches(11.5),
        Inches(0.8),
        "The general objective was met",
        size=30,
        bold=True,
        color=WHITE,
        font="Georgia",
    )
    textbox(
        s,
        Inches(0.8),
        Inches(2.2),
        Inches(11.5),
        Inches(1.1),
        "Ushirika turns supply-chain transactions into clear credit scores. "
        "We compared Random Forest with Logistic Regression on hold-out data, and shipped a live portal for SMEs, lenders and admins.",
        size=15,
        color=MIST,
    )
    for i, (t, d) in enumerate(
        [
            ("Highest priority", "Pilot with partner lenders on real SME ledgers."),
            ("Adopt carefully", "Start with one supply-chain vertical before wider rollout."),
            ("Before production", "Stronger identity checks, managed database, and model audit."),
        ]
    ):
        top = Inches(3.6 + i * 0.75)
        textbox(s, Inches(0.8), top, Inches(3.2), Inches(0.35), t, size=14, bold=True, color=LAGOON_BRIGHT)
        textbox(s, Inches(4.1), top, Inches(8.3), Inches(0.55), d, size=14, color=WHITE)
    textbox(s, Inches(0.8), Inches(6.5), Inches(11.5), Inches(0.4), "Asanteni  ·  Questions and discussion", size=16, bold=True, color=LAGOON_BRIGHT)
    textbox(s, Inches(11.4), Inches(6.5), Inches(1.5), Inches(0.4), "9  /  9", size=12, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)

    for path in (OUT, OUT_SEM2):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            prs.save(str(path))
            print(f"Saved: {path}")
        except PermissionError:
            if path == OUT:
                prs.save(str(OUT_ALT))
                print(f"Original PPT locked; saved: {OUT_ALT}")
            else:
                print(f"Could not write {path} (file may be open).")


if __name__ == "__main__":
    build()
