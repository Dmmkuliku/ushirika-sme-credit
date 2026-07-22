"""
Professional, restrained transitions and limited entrance effects for the
Ushirika Group 15 defence deck (~10 minutes, 12 slides).

Design rules:
- Varied slide transitions (not the same effect every time).
- Very few on-slide animations — only on key moments.
- Effects play in short AfterPrevious / WithPrevious chains so the speaker
  does not click through dozens of shapes.
- No bounce, spin, spiral, or flashy motion.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import win32com.client as win32

SRC = Path(r"C:\Users\USER\OneDrive\Desktop\SEM 2\Data Science Project\Ushirika_Group15.pptx")
CLEAN_BACKUP = SRC.with_name("Ushirika_Group15_BACKUP_before_animations.pptx")
SAFETY_BACKUP = SRC.with_name("Ushirika_Group15_BACKUP_before_professional_pass.pptx")
REPO_COPY = Path(__file__).resolve().parents[1] / "Presentation" / "Ushirika_Group15_Defence_Presentation.pptx"

# Slide transitions (PpEntryEffect)
ppEffectFadeSmoothly = 3845
ppEffectFade = 1793
ppEffectPushLeft = 3857
ppEffectPushRight = 3856
ppEffectPushUp = 3859
ppEffectWipeLeft = 3865
ppEffectWipeRight = 3864
ppEffectWipeUp = 3862
ppEffectUncoverLeft = 3853
ppEffectUncoverRight = 3854

ppTransitionSpeedMedium = 2
ppTransitionSpeedSlow = 1

# Entrance effects (MsoAnimEffect)
msoAnimEffectFade = 10
msoAnimEffectAppear = 1
msoAnimTriggerOnPageClick = 1
msoAnimTriggerWithPrevious = 2
msoAnimTriggerAfterPrevious = 3

msoFalse = 0
msoTrue = -1

# Varied transitions across 12 slides — polished, not repetitive.
# Only use effects accepted by PowerPoint's SlideShowTransition API.
TRANSITIONS = {
    1: (ppEffectFadeSmoothly, ppTransitionSpeedSlow),   # title open
    2: (ppEffectWipeRight, ppTransitionSpeedMedium),     # background
    3: (ppEffectFadeSmoothly, ppTransitionSpeedMedium),  # aim
    4: (ppEffectPushLeft, ppTransitionSpeedMedium),      # what was built
    5: (ppEffectUncoverLeft, ppTransitionSpeedMedium),   # literature
    6: (ppEffectFade, ppTransitionSpeedMedium),          # method
    7: (ppEffectPushRight, ppTransitionSpeedMedium),     # findings 1
    8: (ppEffectPushUp, ppTransitionSpeedMedium),        # findings 2 — metrics impact
    9: (ppEffectWipeLeft, ppTransitionSpeedMedium),      # findings 3
    10: (ppEffectUncoverRight, ppTransitionSpeedMedium), # results vs aim
    11: (ppEffectWipeUp, ppTransitionSpeedMedium),       # discussion
    12: (ppEffectFadeSmoothly, ppTransitionSpeedSlow),   # close
}

# Only these slides get on-slide animation (key moments for a 10-minute talk).
ANIMATED_SLIDES = {1, 8, 10, 12}


def clear_animations(slide) -> None:
    seq = slide.TimeLine.MainSequence
    while seq.Count > 0:
        seq.Item(1).Delete()


def set_transition(slide, effect: int, speed: int) -> None:
    t = slide.SlideShowTransition
    fallbacks = [
        effect,
        ppEffectFadeSmoothly,
        ppEffectFade,
        ppEffectPushLeft,
        ppEffectWipeRight,
    ]
    last_error = None
    for candidate in fallbacks:
        try:
            t.EntryEffect = candidate
            t.Speed = speed
            t.AdvanceOnClick = msoTrue
            t.AdvanceOnTime = msoFalse
            return
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error


def add_effect(slide, shape, effect_id: int, trigger: int, duration: float = 0.45, delay: float = 0.0):
    effect = slide.TimeLine.MainSequence.AddEffect(
        Shape=shape,
        effectId=effect_id,
        trigger=trigger,
    )
    try:
        effect.Timing.Duration = duration
        effect.Timing.TriggerDelayTime = delay
    except Exception:
        pass
    return effect


def content_shapes(slide):
    """Prefer substantial text/content shapes; skip tiny decorations."""
    items = []
    for i in range(1, slide.Shapes.Count + 1):
        shape = slide.Shapes.Item(i)
        try:
            area = float(shape.Width) * float(shape.Height)
            if area < 40_000:  # skip thin bars / tiny glyphs
                continue
            has_text = False
            try:
                has_text = bool(shape.TextFrame.TextRange.Text.strip())
            except Exception:
                has_text = False
            items.append((float(shape.Top), float(shape.Left), -area, has_text, shape))
        except Exception:
            continue
    # Top-first, then left, prefer larger text blocks.
    items.sort(key=lambda row: (row[0], row[1], row[2], 0 if row[3] else 1))
    return [row[4] for row in items]


def animate_key_slide(slide, index: int) -> None:
    shapes = content_shapes(slide)
    if not shapes:
        return

    if index == 1:
        # Title → subtitle/presenter: one click, then gentle cascade.
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.55)
        for shape in shapes[1:3]:
            add_effect(slide, shape, msoAnimEffectFade, msoAnimTriggerAfterPrevious, duration=0.4, delay=0.08)
        return

    if index in (8, 10):
        # Metrics / results: title first, then up to 3 content blocks as one beat.
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.4)
        for i, shape in enumerate(shapes[1:4]):
            trigger = msoAnimTriggerWithPrevious if i > 0 else msoAnimTriggerAfterPrevious
            add_effect(slide, shape, msoAnimEffectFade, trigger, duration=0.4, delay=0.1 if i else 0.05)
        return

    if index == 12:
        # Closing: headline, then closing points.
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.5)
        for shape in shapes[1:4]:
            add_effect(slide, shape, msoAnimEffectFade, msoAnimTriggerAfterPrevious, duration=0.35, delay=0.06)


def process_slide(slide, index: int) -> None:
    clear_animations(slide)
    effect, speed = TRANSITIONS.get(index, (ppEffectFadeSmoothly, ppTransitionSpeedMedium))
    set_transition(slide, effect, speed)
    if index in ANIMATED_SLIDES:
        animate_key_slide(slide, index)


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)

    # Prefer the original pre-animation deck if available.
    source = CLEAN_BACKUP if CLEAN_BACKUP.exists() else SRC
    shutil.copy2(SRC, SAFETY_BACKUP)
    if source != SRC:
        shutil.copy2(source, SRC)
        print(f"Restored clean deck from: {source}")
    print(f"Safety backup: {SAFETY_BACKUP}")

    app = win32.Dispatch("PowerPoint.Application")
    try:
        app.Visible = msoTrue
    except Exception:
        pass

    presentation = app.Presentations.Open(str(SRC), WithWindow=msoFalse)
    try:
        for i in range(1, presentation.Slides.Count + 1):
            process_slide(presentation.Slides.Item(i), i)
            kind = "transition + key animation" if i in ANIMATED_SLIDES else "transition only"
            print(f"Slide {i}: {kind}")
        presentation.Save()
        print(f"Saved: {SRC}")
    finally:
        presentation.Close()
        app.Quit()

    REPO_COPY.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC, REPO_COPY)
    print(f"Repository copy: {REPO_COPY}")


if __name__ == "__main__":
    main()
