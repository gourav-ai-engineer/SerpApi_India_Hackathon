"""AI voice-over for the CareerPilot demo video.

Generates one narration clip per chapter with Kokoro, an open-source text-to-speech
model that runs offline, and mixes the clips into a recorded video at each chapter's
start time. `tools/record_demo.py --voice` calls this automatically. The steps can
also be run by hand:

    python tools/narration.py tts                 # write recordings/narration/*.wav
    python tools/narration.py mux VIDEO.webm      # VIDEO.webm + chapters -> VIDEO.mp4

Needs: pip install kokoro-onnx soundfile imageio-ffmpeg
The first run downloads the model files (~350 MB) from the kokoro-onnx GitHub releases.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/{name}"
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
VOICE = "am_michael"
SPEED = 1.08

# One block per chapter in record_demo.py. Keep in sync with VOICEOVER.md.
SCRIPT: list[tuple[str, str]] = [
    ("1 Hook",
     "Job hunting means duplicated, stale listings, and no idea why a role fits you. "
     "CareerPilot is an AI agent that fixes that, using live data from SerpApi."),
    ("2 Keys and search budget",
     "API keys stay on the server and never appear in the page. "
     "In the sidebar, I set the agent's budget: queries, result pages, and cross-checks."),
    ("3 Profile and resume skills",
     "I enter my target role and location, then paste my resume. "
     "Skills are detected locally, nothing is uploaded, and added to my profile."),
    ("4 Agent run",
     "Now the agent plans its queries, searches Google Jobs through SerpApi, follows pagination, "
     "merges duplicates, ranks every role, and verifies the top results."),
    ("5 Run summary",
     "The summary shows unique roles, strong fits, and the exact number of SerpApi calls. "
     "Repeat searches are cached, so credits aren't wasted."),
    ("6 Job card",
     "Each job gets a colour-coded fit score, the skills it matched, and an evidence badge."),
    ("7 Score breakdown and sources",
     "The score explains itself: role, skills, location, seniority, and freshness. "
     "It's a ranking aid, not a hiring prediction."),
    ("8 Filters and sorting",
     "I can filter by fit score, search by keyword, or sort by evidence. "
     "For top results, a second SerpApi search on Google looks for the employer's own careers page. "
     "Anything uncertain is clearly labelled, never hidden."),
    ("9 Export",
     "The shortlist exports to CSV, safe for Excel."),
    ("10 Market insights",
     "Market insights turn these listings into advice. "
     "Green skills, I already have. Blue skills are gaps worth learning next. "
     "It also shows who is hiring most."),
    ("11 Application tracker",
     "I save a promising role to my tracker, update its status, and add a follow-up note. "
     "It all stays on my machine and exports to CSV."),
    ("12 Agent trace",
     "The agent trace records every query, page, and check, so every decision is reviewable."),
    ("13 Method and limits",
     "Scoring weights, evidence labels, and known limits are documented in the app."),
    ("14 Close",
     "CareerPilot: live discovery with SerpApi, verified evidence, explainable ranking, "
     "and skill-gap insights. It even runs from the command line. Thanks for watching!"),
]


def _slug(title: str) -> str:
    return title.split(" ", 1)[0].zfill(2)


def ensure_models(model_dir: Path) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        target = model_dir / name
        if not target.exists():
            print(f"Downloading {name} …")
            partial = target.with_suffix(target.suffix + ".part")
            urllib.request.urlretrieve(MODEL_URL.format(name=name), partial)
            partial.rename(target)


def generate(out_dir: Path, model_dir: Path) -> dict[str, float]:
    """Write one WAV per chapter and return {chapter title: seconds}."""
    import soundfile as sf
    from kokoro_onnx import Kokoro

    ensure_models(model_dir)
    kokoro = Kokoro(str(model_dir / MODEL_FILES[0]), str(model_dir / MODEL_FILES[1]))
    out_dir.mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}
    for title, text in SCRIPT:
        samples, rate = kokoro.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        sf.write(out_dir / f"{_slug(title)}.wav", samples, rate)
        durations[title] = round(len(samples) / rate, 2)
        print(f"{title}: {durations[title]:.1f}s")
    (out_dir / "durations.json").write_text(json.dumps(durations, indent=2), encoding="utf-8")
    print(f"Total narration: {sum(durations.values()):.0f}s")
    return durations


def load_durations(out_dir: Path) -> dict[str, float]:
    path = out_dir / "durations.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def mux(video: Path, narration_dir: Path, starts: dict[str, float]) -> Path:
    """Place each chapter's clip at its start time (seconds into the video) and encode an MP4."""
    inputs: list[str] = ["-i", str(video)]
    filters: list[str] = []
    labels: list[str] = []
    for index, (title, _) in enumerate(SCRIPT, start=1):
        clip = narration_dir / f"{_slug(title)}.wav"
        if title not in starts or not clip.exists():
            continue
        inputs += ["-i", str(clip)]
        delay = max(0, int(starts[title] * 1000))
        filters.append(f"[{len(labels) + 1}:a]adelay={delay}|{delay},apad[a{index}]")
        labels.append(f"[a{index}]")
    if not labels:
        raise SystemExit("No narration clips matched the recorded chapters.")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,"
                   f"loudnorm=I=-16:TP=-1.5[voice]")
    target = video.with_suffix(".mp4")
    command = [
        ffmpeg_exe(), "-y", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "0:v", "-map", "[voice]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(target),
    ]
    subprocess.run(command, check=True)
    return target


def read_chapters(video: Path) -> dict[str, float]:
    """Parse the chapters file written by record_demo.py (lines like '1:23.4  6 Job card')."""
    starts: dict[str, float] = {}
    for line in video.with_suffix(".chapters.txt").read_text(encoding="utf-8").splitlines():
        stamp, _, title = line.strip().partition("  ")
        if not title or title == "end":
            continue
        minutes, seconds = stamp.split(":")
        starts[title.strip()] = int(minutes) * 60 + float(seconds)
    return starts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and mix the AI voice-over.")
    sub = parser.add_subparsers(dest="command", required=True)
    tts = sub.add_parser("tts", help="Generate narration clips")
    tts.add_argument("--out", default="recordings/narration")
    tts.add_argument("--models", default="recordings/models")
    mix = sub.add_parser("mux", help="Mix narration into a recorded video")
    mix.add_argument("video")
    mix.add_argument("--narration", default="recordings/narration")
    args = parser.parse_args()
    if args.command == "tts":
        generate(Path(args.out), Path(args.models))
    else:
        video = Path(args.video)
        print(f"Saved {mux(video, Path(args.narration), read_chapters(video))}")


if __name__ == "__main__":
    main()
