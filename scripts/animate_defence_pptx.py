"""
Professional, restrained transitions and limited entrance effects for the
Ushirika Group 15 defence deck (9 slides).

Design rules:
- Varied slide transitions (not the same effect every time).
- Very few on-slide animations — only on key moments.
- Effects play in short AfterPrevious / WithPrevious chains.
- No bounce, spin, spiral, or flashy motion.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import win32com.client as win32

SRC = Path(__file__).resolve().parents[1] / "Presentation" / "Ushirika_Group15_Defence_Presentation.pptx"
SRC_ALT = Path(__file__).resolve().parents[1] / "Presentation" / "Ushirika_Group15_Defence_v13.pptx"
SEM2 = Path(r"C:\Users\USER\OneDrive\Desktop\SEM 2\Data Science Project\Ushirika_Group15.pptx")
SAFETY_BACKUP = SRC.with_name("Ushirika_Group15_BACKUP_before_professional_pass.pptx")
REPO_COPY = SRC  # already the primary target


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
msoAnimTriggerOnPageClick = 1
msoAnimTriggerWithPrevious = 2
msoAnimTriggerAfterPrevious = 3

msoFalse = 0
msoTrue = -1

# Varied transitions across 9 slides
TRANSITIONS = {
    1: (ppEffectFadeSmoothly, ppTransitionSpeedSlow),
    2: (ppEffectWipeRight, ppTransitionSpeedMedium),
    3: (ppEffectFadeSmoothly, ppTransitionSpeedMedium),
    4: (ppEffectPushLeft, ppTransitionSpeedMedium),
    5: (ppEffectUncoverLeft, ppTransitionSpeedMedium),
    6: (ppEffectFade, ppTransitionSpeedMedium),
    7: (ppEffectPushUp, ppTransitionSpeedMedium),
    8: (ppEffectWipeLeft, ppTransitionSpeedMedium),
    9: (ppEffectFadeSmoothly, ppTransitionSpeedSlow),
}

# Key moments only — light fades, not busy
ANIMATED_SLIDES = {1, 2, 7, 8, 9}


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
    items = []
    for i in range(1, slide.Shapes.Count + 1):
        shape = slide.Shapes.Item(i)
        try:
            area = float(shape.Width) * float(shape.Height)
            if area < 40_000:
                continue
            has_text = False
            try:
                has_text = bool(shape.TextFrame.TextRange.Text.strip())
            except Exception:
                has_text = False
            items.append((float(shape.Top), float(shape.Left), -area, has_text, shape))
        except Exception:
            continue
    items.sort(key=lambda row: (row[0], row[1], row[2], 0 if row[3] else 1))
    return [row[4] for row in items]


def animate_key_slide(slide, index: int) -> None:
    shapes = content_shapes(slide)
    if not shapes:
        return

    if index == 1:
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.5)
        for shape in shapes[1:4]:
            add_effect(slide, shape, msoAnimEffectFade, msoAnimTriggerAfterPrevious, duration=0.35, delay=0.06)
        return

    if index == 2:
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.35)
        for i, shape in enumerate(shapes[1:5]):
            trigger = msoAnimTriggerWithPrevious if i % 2 else msoAnimTriggerAfterPrevious
            add_effect(slide, shape, msoAnimEffectFade, trigger, duration=0.35, delay=0.05)
        return

    if index in (7, 8):
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.4)
        for i, shape in enumerate(shapes[1:5]):
            trigger = msoAnimTriggerWithPrevious if i > 0 else msoAnimTriggerAfterPrevious
            add_effect(slide, shape, msoAnimEffectFade, trigger, duration=0.35, delay=0.08 if i else 0.05)
        return

    if index == 9:
        add_effect(slide, shapes[0], msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.45)
        for shape in shapes[1:4]:
            add_effect(slide, shape, msoAnimEffectFade, msoAnimTriggerAfterPrevious, duration=0.35, delay=0.06)


def process_slide(slide, index: int) -> None:
    clear_animations(slide)
    effect, speed = TRANSITIONS.get(index, (ppEffectFadeSmoothly, ppTransitionSpeedMedium))
    set_transition(slide, effect, speed)
    if index in ANIMATED_SLIDES:
        animate_key_slide(slide, index)


def main() -> None:
    candidates = [p for p in (SRC, SRC_ALT, SEM2) if p.exists()]
    if not candidates:
        raise FileNotFoundError(SRC)
    # Prefer the newest built deck so a locked older file is not re-animated over a fresh build
    target = max(candidates, key=lambda p: p.stat().st_mtime)
    print(f"Animating: {target}")

    try:
        shutil.copy2(target, SAFETY_BACKUP)
        print(f"Safety backup: {SAFETY_BACKUP}")
    except Exception as exc:
        print(f"Backup skipped: {exc}")

    app = win32.Dispatch("PowerPoint.Application")
    app.Visible = 1
    presentation = app.Presentations.Open(str(target), WithWindow=True)

    saved_path = target
    try:
        count = presentation.Slides.Count
        print(f"Animating {count} slides…")
        for i in range(1, count + 1):
            process_slide(presentation.Slides.Item(i), i)
            print(f"  slide {i}: transition + {'entrance' if i in ANIMATED_SLIDES else 'no entrance'}")
        try:
            presentation.Save()
            print(f"Saved: {target}")
        except Exception:
            presentation.SaveAs(str(SRC_ALT))
            saved_path = SRC_ALT
            print(f"Primary locked; saved: {SRC_ALT}")
    finally:
        presentation.Close()
        app.Quit()

    for dest in (SRC, SRC_ALT, SEM2):
        if dest == saved_path:
            continue
        try:
            shutil.copy2(saved_path, dest)
            print(f"Synced: {dest}")
        except Exception as exc:
            print(f"Could not sync {dest}: {exc}")


if __name__ == "__main__":
    main()
