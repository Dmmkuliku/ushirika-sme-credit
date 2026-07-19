"""
Ushirika / Group 15 defence presentation (max 12 slides).
Structure mirrors BOT-final presentation (Findings): title → background → aim →
what was built → literature gap → method → findings → results vs aim → discussion → close.
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parent / "Ushirika_Group15_Defence_Presentation.pptx"
OUT_ALT = Path(__file__).resolve().parent / "Ushirika_Group15_Defence_v13.pptx"

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
LINE = RGBColor(0xC5, 0xD2, 0xD5)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
TOTAL = 12


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


def footer(slide, page, title="USHIRIKA — SME VALUE CHAIN CREDIT RISK"):
    rect(slide, Inches(0), Inches(7.15), SLIDE_W, Inches(0.35), FOREST_DEEP)
    textbox(slide, Inches(0.45), Inches(7.18), Inches(10), Inches(0.28), title, size=10, color=RGBColor(0xB8, 0xD0, 0xC8))
    textbox(slide, Inches(11.4), Inches(7.18), Inches(1.5), Inches(0.28), f"{page}  /  {TOTAL}", size=10, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)


def bg(slide, color=PAPER):
    rect(slide, Inches(0), Inches(0), SLIDE_W, SLIDE_H, color)


def section_header(slide, kicker, title, subtitle=None):
    textbox(slide, Inches(0.55), Inches(0.28), Inches(12), Inches(0.28), kicker, size=12, bold=True, color=LAGOON)
    rect(slide, Inches(0.55), Inches(0.62), Inches(0.1), Inches(0.48), LAGOON_BRIGHT)
    textbox(slide, Inches(0.8), Inches(0.55), Inches(11.8), Inches(0.5), title, size=26, bold=True, color=FOREST, font="Georgia")
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
    textbox(s, Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.35), "EASTERN AFRICA STATISTICAL TRAINING CENTRE  ·  CAPSTONE PROJECT DEFENCE", size=12, bold=True, color=LAGOON_BRIGHT)
    textbox(s, Inches(0.8), Inches(1.25), Inches(11.5), Inches(1.3), "Development of a Machine Learning-Based\nCredit Risk Assessment Model for SME\nValue Chain Financing", size=28, bold=True, color=WHITE, font="Georgia")
    textbox(s, Inches(0.8), Inches(2.75), Inches(11.5), Inches(0.4), "A Case Study of Tanzania’s Supply Chains  ·  Platform: Ushirika", size=16, color=MIST)
    textbox(s, Inches(0.8), Inches(3.4), Inches(11.5), Inches(1.6),
            "PRESENTED BY — GROUP 15\n"
            "Herman Edward Mkumbwa  ·  Raymond Elphance Tungaraza  ·  Edwin Celestin Silayo\n"
            "Grace Joachim Mohammed  ·  Priscila Nestor Mpembela\n\n"
            "SUPERVISOR: Mr. Rajabu Msangi\n"
            "Bachelor of Data Science (Year III)  ·  Academic Year 2025/2026",
            size=13, color=RGBColor(0xB8, 0xD0, 0xC8))
    textbox(s, Inches(0.8), Inches(6.7), Inches(10), Inches(0.3), "Live portal: ushirika-sme-portal.vercel.app   ·   API: ushirika-api.onrender.com", size=11, color=RGBColor(0x9B, 0xC4, 0xBA))
    textbox(s, Inches(11.4), Inches(6.7), Inches(1.5), Inches(0.3), "1  /  12", size=11, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)

    # 2 Background
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "BACKGROUND", "Why Tanzanian SMEs still struggle to get fair credit", "Grounded in the Group 15 problem statement (Section 1.2)")
    cards = [
        ("01", "Collateral-heavy credit", "Banks still rely on collateral and formal statements that most Tanzanian SMEs do not have."),
        ("02", "Static risk metrics", "Backward-looking ratios misclassify viable businesses operating in informal or semi-formal supply chains."),
        ("03", "Unused transaction signals", "Buyer–supplier payment behaviour is rich risk data, but no integrated platform captures and scores it."),
        ("04", "Missing-middle gap", "Without alternative scoring, creditworthy SMEs stay outside formal finance — the financing gap persists."),
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
    section_header(s, "AIM OF THE PROJECT", "What we set out to build — in clear terms")
    round_rect(s, Inches(0.5), Inches(1.65), Inches(12.3), Inches(1.35), WHITE)
    textbox(s, Inches(0.75), Inches(1.8), Inches(11.8), Inches(0.3), "GENERAL OBJECTIVE", size=11, bold=True, color=LAGOON)
    textbox(s, Inches(0.75), Inches(2.15), Inches(11.8), Inches(0.7),
            "To develop an automated, data-driven ecosystem banking platform that leverages supply chain transaction data and machine learning techniques to provide accurate and inclusive credit risk assessments for SMEs in Tanzania.",
            size=14, color=INK)
    objs = [
        ("01", "Preprocessing & features", "Build robust pipelines that convert raw supply-chain transactions into predictive variables."),
        ("02", "Compare ML vs classical", "Evaluate ensemble learning (Random Forest) against classical Logistic Regression."),
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
    section_header(s, "WHAT WAS BUILT", "Ushirika — a working credit platform for SMEs and lenders", "Deliverables match proposal Section 3.10")
    layers = [
        ("Frontend", "Vite + JS/CSS\nSME · Lender · Admin\nTabbed lender detail\nEN / Kiswahili UI", LAGOON),
        ("API", "FastAPI + JWT\nTransactions + TIN\nRole-based access", FOREST),
        ("ML Core", "Feature engineering\nRF (primary) + LR\n80/20 train–test + CV", LAGOON_BRIGHT),
        ("Data & Ethics", "SQL storage\nHMAC PII hashes\n25% outlier rule\nConservative loans", FOREST_DEEP),
    ]
    for i, (t, d, c) in enumerate(layers):
        left = Inches(0.45 + i * 3.2)
        round_rect(s, left, Inches(1.75), Inches(3.0), Inches(3.4), WHITE)
        rect(s, left, Inches(1.75), Inches(3.0), Inches(0.6), c)
        textbox(s, left + Inches(0.15), Inches(1.88), Inches(2.7), Inches(0.35), t, size=15, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, left + Inches(0.25), Inches(2.6), Inches(2.5), Inches(2.2), d, size=13, color=INK, align=PP_ALIGN.CENTER)
        if i < 3:
            textbox(s, left + Inches(2.85), Inches(3.2), Inches(0.4), Inches(0.35), "→", size=20, bold=True, color=LAGOON, align=PP_ALIGN.CENTER)
    textbox(s, Inches(0.55), Inches(5.45), Inches(12.2), Inches(1.2),
            "Proposal fulfilment: operational ML backend · Vite interactive portal · technical performance report.\n"
            "Lender workflow: progressive NIDA search → SME profile (incl. TIN) → tabs for ML metrics, signals, txs, history.",
            size=13, color=MUTED)
    footer(s, 4)

    # 5 Literature gap
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "LITERATURE REVIEW", "What the literature establishes, and what it leaves out")
    cites = [
        ("Breiman (2001)", "Ensemble Random Forests capture non-linear patterns better than single models."),
        ("Lessmann et al. (2015)", "Ensemble classifiers outperform classical baselines on credit-scoring benchmarks."),
        ("Khandani et al. (2010)", "Transactional / alternative data can proxy creditworthiness where statements are thin."),
        ("Klapper (2006)", "Value-chain financing uses buyer–supplier relationships instead of collateral alone."),
    ]
    for i, (a, b) in enumerate(cites):
        top = Inches(1.65 + i * 0.85)
        round_rect(s, Inches(0.5), top, Inches(7.4), Inches(0.75), WHITE)
        textbox(s, Inches(0.7), top + Inches(0.12), Inches(7.0), Inches(0.25), a, size=13, bold=True, color=FOREST)
        textbox(s, Inches(0.7), top + Inches(0.4), Inches(7.0), Inches(0.3), b, size=12, color=MUTED)
    round_rect(s, Inches(8.2), Inches(1.65), Inches(4.6), Inches(4.7), FOREST)
    textbox(s, Inches(8.45), Inches(1.9), Inches(4.1), Inches(0.35), "THE GAP (TZ context)", size=14, bold=True, color=LAGOON_BRIGHT)
    bullets(s, Inches(8.45), Inches(2.45), Inches(4.1), Inches(3.6), [
        "Few integrated platforms join live SME transactions with ML scoring.",
        "Most benchmarks use developed-market data, not informal Tanzanian chains.",
        "Supply-chain signals remain under-used as alternative credit metrics.",
        "Ushirika operationalises that gap as a working prototype.",
    ], size=13, color=WHITE)
    footer(s, 5)

    # 6 Method
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "EVALUATION METHOD", "How we trained and tested the models fairly")
    round_rect(s, Inches(0.5), Inches(1.65), Inches(6.1), Inches(4.7), WHITE)
    textbox(s, Inches(0.75), Inches(1.85), Inches(5.6), Inches(0.35), "TRAINING PROTOCOL", size=14, bold=True, color=LAGOON)
    bullets(s, Inches(0.75), Inches(2.35), Inches(5.6), Inches(3.7), [
        "Features from payment behaviour, volume, delays, partner diversity, intervals.",
        "80/20 stratified train_test_split (random_state=42).",
        "Models fit on training fold only; GridSearchCV (ROC-AUC).",
        "Hold-out metrics on unseen test set: Acc, Precision, Recall, F1, ROC-AUC.",
        "Live SME histories are mixed into retrain after enough transactions.",
        "Outlier rule: rare large deals (<25% of txs) are excluded from loan sizing; frequent large deals count as pattern.",
    ], size=13)
    round_rect(s, Inches(6.9), Inches(1.65), Inches(5.9), Inches(4.7), WHITE)
    textbox(s, Inches(7.15), Inches(1.85), Inches(5.4), Inches(0.35), "TWO MODELS COMPARED", size=14, bold=True, color=LAGOON)
    bullets(s, Inches(7.15), Inches(2.35), Inches(5.4), Inches(3.7), [
        "Baseline: Logistic Regression + StandardScaler.",
        "Primary: Random Forest Classifier (ensemble).",
        "Selection metric: ROC-AUC on hold-out test data.",
        "Artifacts: .joblib models + model_meta.json.",
        "Runtime: CreditPredictor maps probability → score (~300–680).",
        "Risk bands: Low ≥580 · Medium 480–579 · High <480.",
    ], size=13)
    footer(s, 6)

    # 7 Findings SO1
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "FINDINGS — OBJECTIVE 1", "Raw supply-chain data → predictive variables")
    feats = [
        ("Payment reliability", "Consistency of completed payments"),
        ("Delay & on-time rates", "Average/max delay; payments within due window"),
        ("Volume & frequency", "Turnover (TZS), deals per month, volume trend"),
        ("Partner diversity", "Unique counterparties / transaction mix"),
        ("Interval risk", "Average days between consecutive deals"),
        ("Outlier handling", "25% frequency guard: rare spikes excluded from loan; pattern large deals kept"),
    ]
    for i, (t, d) in enumerate(feats):
        left = Inches(0.5 + (i % 3) * 4.2)
        top = Inches(1.7 + (i // 3) * 2.35)
        round_rect(s, left, top, Inches(4.0), Inches(2.1), WHITE)
        rect(s, left, top, Inches(4.0), Inches(0.12), LAGOON_BRIGHT)
        textbox(s, left + Inches(0.3), top + Inches(0.4), Inches(3.4), Inches(0.45), t, size=15, bold=True, color=FOREST)
        textbox(s, left + Inches(0.3), top + Inches(1.0), Inches(3.4), Inches(0.8), d, size=13, color=MUTED)
    footer(s, 7)

    # 8 Findings SO2
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "FINDINGS — OBJECTIVE 2", "Ensemble Random Forest outperforms classical Logistic Regression")
    metric(s, Inches(0.5), Inches(1.7), Inches(3.0), Inches(1.35), "88.5%", "RF ROC-AUC (primary)", SUCCESS)
    metric(s, Inches(3.7), Inches(1.7), Inches(3.0), Inches(1.35), "84.2%", "RF Accuracy", LAGOON)
    metric(s, Inches(6.9), Inches(1.7), Inches(3.0), Inches(1.35), "75.4%", "LR ROC-AUC (baseline)", RGBColor(0x8A, 0x5A, 0x00))
    metric(s, Inches(10.1), Inches(1.7), Inches(2.7), Inches(1.35), "RF wins", "Outperforms baseline", FOREST)
    round_rect(s, Inches(0.5), Inches(3.35), Inches(12.3), Inches(3.1), WHITE)
    textbox(s, Inches(0.8), Inches(3.55), Inches(11.7), Inches(0.35), "Hold-out comparison (seed=42) — metrics from model_meta.json", size=14, bold=True, color=FOREST)
    bullets(s, Inches(0.8), Inches(4.1), Inches(11.7), Inches(2.1), [
        "Random Forest: Accuracy 84.2% · Precision 85.7% · Recall 52.9% · F1 65.5% · ROC-AUC 88.5%.",
        "Logistic Regression: Accuracy 74.6% · Precision 64.0% · Recall 23.5% · F1 34.4% · ROC-AUC 75.4%.",
        "This answers Research Question 2: ensemble learning improves classification relative to classical regression on this task.",
        "Evidence is reproducible via scripts/train_model.py and stored artifacts under Backend/models/.",
    ], size=14)
    footer(s, 8)

    # 9 Findings SO3 + reliability
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "FINDINGS — OBJECTIVE 3", "Industry-standard metrics support an objective scoring process")
    round_rect(s, Inches(0.5), Inches(1.7), Inches(6.1), Inches(4.7), WHITE)
    textbox(s, Inches(0.75), Inches(1.9), Inches(5.6), Inches(0.35), "RELIABILITY CONTROLS", size=14, bold=True, color=LAGOON)
    bullets(s, Inches(0.75), Inches(2.4), Inches(5.6), Inches(3.7), [
        "Hold-out ROC-AUC, Accuracy, Precision, Recall, F1 reported for both models.",
        "k-fold GridSearchCV on the training split reduces overfitting risk.",
        "Minimum 5 transactions before an SME is scored.",
        "Conservative score mapping (~300–680) and explicit risk bands.",
        "Financing capped at ~50% of typical (non-outlier) volume — reduces unpaid-loan risk.",
        "Technical Performance Report documents honesty of evaluation.",
    ], size=13)
    round_rect(s, Inches(6.9), Inches(1.7), Inches(5.9), Inches(4.7), WHITE)
    textbox(s, Inches(7.15), Inches(1.9), Inches(5.4), Inches(0.35), "RUNTIME OUTPUTS", size=14, bold=True, color=LAGOON)
    bullets(s, Inches(7.15), Inches(2.4), Inches(5.4), Inches(3.7), [
        "Credit score + risk band (Low / Medium / High).",
        "Eligible financing (TZS) with 25% outlier-aware caps.",
        "Crucial score signals only (not every engineered feature).",
        "Lender: progressive NIDA search + tabbed SME analytics.",
        "TIN shown on SME profile (SME + Lender views).",
        "Bilingual portal (English / Kiswahili) end-to-end.",
    ], size=13)
    footer(s, 9)

    # 10 Results against aim
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "RESULTS AGAINST AIM", "All three specific objectives were achieved")
    rows = [
        ("1", "Preprocessing & feature engineering", "Transaction pipelines produce 13 engineered predictors + outlier flags used for scoring and financing."),
        ("2", "Ensemble vs classical regression", "RF and LR trained on identical split; RF wins on ROC-AUC (88.5% vs 75.4%)."),
        ("3", "Industry-standard evaluation", "Accuracy, Precision, Recall, F1, ROC-AUC stored and used to select the primary model."),
    ]
    for i, (num, title, body) in enumerate(rows):
        top = Inches(1.7 + i * 1.55)
        round_rect(s, Inches(0.5), top, Inches(12.3), Inches(1.4), WHITE)
        rect(s, Inches(0.5), top, Inches(0.7), Inches(1.4), FOREST if i != 1 else LAGOON)
        textbox(s, Inches(0.55), top + Inches(0.45), Inches(0.6), Inches(0.45), num, size=22, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        textbox(s, Inches(1.5), top + Inches(0.25), Inches(9.5), Inches(0.35), title, size=16, bold=True, color=FOREST)
        textbox(s, Inches(1.5), top + Inches(0.7), Inches(9.5), Inches(0.5), body, size=13, color=MUTED)
        met_badge(s, Inches(11.6), top + Inches(0.5))
    footer(s, 10)

    # 11 Discussion
    s = prs.slides.add_slide(blank)
    bg(s)
    section_header(s, "DISCUSSION", "How findings compare with the literature — and remaining limits")
    round_rect(s, Inches(0.5), Inches(1.65), Inches(6.1), Inches(4.7), WHITE)
    textbox(s, Inches(0.75), Inches(1.85), Inches(5.6), Inches(0.35), "CONFIRMED IN OUR PROTOTYPE", size=14, bold=True, color=LAGOON)
    bullets(s, Inches(0.75), Inches(2.35), Inches(5.6), Inches(3.7), [
        "Breiman / Lessmann: ensemble RF beats linear LR on this credit task.",
        "Khandani: transaction behaviour can score SMEs without full statements.",
        "Klapper: value-chain style signals (counterparties, intervals, volume) support lending decisions.",
        "Altman tradition extended: from static ratios to dynamic behavioural classification.",
    ], size=13)
    round_rect(s, Inches(6.9), Inches(1.65), Inches(5.9), Inches(4.7), WHITE)
    textbox(s, Inches(7.15), Inches(1.85), Inches(5.4), Inches(0.35), "LIMITATIONS & NEXT STEPS", size=14, bold=True, color=LAGOON)
    bullets(s, Inches(7.15), Inches(2.35), Inches(5.4), Inches(3.7), [
        "Prototype scope — not yet a full bank production system.",
        "Training still relies partly on synthetic bootstrap when live SMEs are few.",
        "Need larger, multi-sector Tanzanian transaction panels.",
        "Future: XGBoost/GBM, live ERP connectors, stronger model monitoring.",
        "Future: formal NIDA verification and managed Postgres.",
    ], size=13)
    footer(s, 11)

    # 12 Conclusion
    s = prs.slides.add_slide(blank)
    bg(s, FOREST_DEEP)
    rect(s, Inches(0), Inches(0), Inches(0.35), SLIDE_H, LAGOON_BRIGHT)
    textbox(s, Inches(0.8), Inches(0.7), Inches(11.5), Inches(0.3), "CONCLUSION", size=12, bold=True, color=LAGOON_BRIGHT)
    textbox(s, Inches(0.8), Inches(1.15), Inches(11.5), Inches(0.9), "The general objective was met", size=30, bold=True, color=WHITE, font="Georgia")
    textbox(s, Inches(0.8), Inches(2.15), Inches(11.5), Inches(1.1),
            "Ushirika is a working prototype that turns supply-chain transactions into objective credit scores — "
            "with real train/test ML, RF vs LR evidence, and a live portal for Mfanyabiashara, Afisa mikopo, and Admin.",
            size=15, color=MIST)
    for i, (t, d) in enumerate([
        ("Highest priority", "Pilot with partner lenders on real SME ledgers and monitor drift."),
        ("Adopt incrementally", "Start with one supply-chain vertical before nationwide rollout."),
        ("Before production", "Managed database, stronger identity checks, and continuous model audit."),
    ]):
        top = Inches(3.5 + i * 0.85)
        textbox(s, Inches(0.8), top, Inches(3.2), Inches(0.35), t, size=14, bold=True, color=LAGOON_BRIGHT)
        textbox(s, Inches(4.1), top, Inches(8.3), Inches(0.7), d, size=14, color=WHITE)
    textbox(s, Inches(0.8), Inches(6.5), Inches(11.5), Inches(0.4), "Asanteni  ·  Questions and discussion", size=16, bold=True, color=LAGOON_BRIGHT)
    textbox(s, Inches(11.4), Inches(6.5), Inches(1.5), Inches(0.4), "12  /  12", size=12, color=RGBColor(0xB8, 0xD0, 0xC8), align=PP_ALIGN.RIGHT)

    try:
        prs.save(str(OUT))
        print(f"Saved: {OUT}")
    except PermissionError:
        prs.save(str(OUT_ALT))
        print(f"Original PPT locked; saved: {OUT_ALT}")


if __name__ == "__main__":
    build()
