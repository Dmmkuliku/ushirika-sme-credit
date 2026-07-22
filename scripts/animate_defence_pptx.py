"""
Add professional, panel-ready transitions and entrance animations
to the Ushirika Group 15 defence deck via PowerPoint COM.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import win32com.client as win32

SRC = Path(r"C:\Users\USER\OneDrive\Desktop\SEM 2\Data Science Project\Ushirika_Group15.pptx")
BACKUP = SRC.with_name("Ushirika_Group15_BACKUP_before_animations.pptx")
REPO_COPY = Path(__file__).resolve().parents[1] / "Presentation" / "Ushirika_Group15_Defence_Presentation.pptx"

# PowerPoint constants
ppEffectFadeSmoothly = 3845
ppEffectPushLeft = 3857
ppEffectCoverLeft = 3841
ppTransitionSpeedMedium = 2
ppTransitionSpeedSlow = 1
msoAnimEffectFade = 10
msoAnimEffectFloatUp = 33
msoAnimEffectAppear = 1
msoAnimTriggerOnPageClick = 1
msoAnimTriggerWithPrevious = 2
msoAnimTriggerAfterPrevious = 3
msoFalse = 0
msoTrue = -1


def clear_animations(slide) -> None:
    seq = slide.TimeLine.MainSequence
    while seq.Count > 0:
        seq.Item(1).Delete()


def set_transition(slide, effect: int, speed: int = ppTransitionSpeedMedium) -> None:
    t = slide.SlideShowTransition
    t.EntryEffect = effect
    t.Speed = speed
    t.AdvanceOnClick = msoTrue
    t.AdvanceOnTime = msoFalse


def add_effect(slide, shape, effect_id: int, trigger: int, duration: float = 0.55, delay: float = 0.0):
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


def animate_slide(slide, index: int) -> None:
    clear_animations(slide)
    shapes = [slide.Shapes.Item(i) for i in range(1, slide.Shapes.Count + 1)]
    # Prefer larger / higher text shapes first so titles lead the sequence.
    shapes.sort(key=lambda s: (-float(s.Top), float(s.Left)))

    if index == 1:
        set_transition(slide, ppEffectFadeSmoothly, ppTransitionSpeedSlow)
    elif index in (8, 10, 12):
        set_transition(slide, ppEffectPushLeft, ppTransitionSpeedMedium)
    else:
        set_transition(slide, ppEffectFadeSmoothly, ppTransitionSpeedMedium)

    # Skip pure decorative lines/rects that are too thin to animate meaningfully.
    candidates = []
    for shape in shapes:
        try:
            if shape.Width < 20 and shape.Height < 20:
                continue
            # Keep thin accent bars; animate content blocks and text.
            candidates.append(shape)
        except Exception:
            continue

    if not candidates:
        return

    # Title / first content: fade in on click. Remaining items cascade after previous.
    first = candidates[0]
    add_effect(slide, first, msoAnimEffectFade, msoAnimTriggerOnPageClick, duration=0.6)

    for i, shape in enumerate(candidates[1:], start=1):
        # Alternate subtle float-up with fade for a polished but restrained look.
        effect_id = msoAnimEffectFloatUp if i % 3 == 0 else msoAnimEffectFade
        # Group pairs with previous to avoid too many clicks during defence.
        trigger = msoAnimTriggerWithPrevious if i % 2 == 1 else msoAnimTriggerAfterPrevious
        delay = 0.12 if trigger == msoAnimTriggerWithPrevious else 0.05
        add_effect(slide, shape, effect_id, trigger, duration=0.5, delay=delay)


def main() -> None:
    if not SRC.exists():
        raise FileNotFoundError(SRC)

    shutil.copy2(SRC, BACKUP)
    print(f"Backup: {BACKUP}")

    app = win32.Dispatch("PowerPoint.Application")
    # Keep PowerPoint invisible for a clean automation run.
    try:
        app.Visible = msoTrue
    except Exception:
        pass

    presentation = app.Presentations.Open(str(SRC), WithWindow=msoFalse)
    try:
        for i in range(1, presentation.Slides.Count + 1):
            slide = presentation.Slides.Item(i)
            animate_slide(slide, i)
            print(f"Animated slide {i}/{presentation.Slides.Count}")

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
