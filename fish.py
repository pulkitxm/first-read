import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

FISH_URL = "https://api.fish.audio/v1/tts"


def load_env(root: Path):
    path = root / ".env"
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def speak_chunks(chunks):
    key = os.environ.get("FISH_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set FISH_API_KEY. Create one under API Keys on the Fish Audio developer dashboard. The examples already play.")
    parts = [_post(key, chunk) for chunk in chunks]
    if len(parts) == 1:
        return parts[0]
    return _join(parts)


def _post(key, chunk):
    payload = json.dumps(
        {
            "text": chunk["text"],
            "reference_id": chunk["voice_ids"],
            "format": "mp3",
            "mp3_bitrate": 128,
            "latency": "normal",
        }
    ).encode()
    request = urllib.request.Request(
        FISH_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "model": "drama-3",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            audio = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:240]
        raise RuntimeError(f"Fish Audio returned {error.code}. {detail}") from error
    if not audio:
        raise RuntimeError("Fish Audio returned empty audio.")
    return audio


def _join(parts):
    with tempfile.TemporaryDirectory() as folder:
        paths = []
        for index, audio in enumerate(parts):
            path = Path(folder) / f"{index}.mp3"
            path.write_bytes(audio)
            paths.append(path)
        out = Path(folder) / "read.mp3"
        inputs = []
        for path in paths:
            inputs.extend(["-i", str(path)])
        count = len(paths)
        pads = []
        labels = []
        for index in range(count):
            if index < count - 1:
                pads.append(f"[{index}:a]apad=pad_dur=0.35[a{index}]")
                labels.append(f"[a{index}]")
            else:
                labels.append(f"[{index}:a]")
        filt = ";".join(pads) + ";" + "".join(labels) + f"concat=n={count}:v=0:a=1[a]"
        subprocess.run(
            ["ffmpeg", "-y", *inputs, "-filter_complex", filt, "-map", "[a]", "-c:a", "libmp3lame", "-b:a", "128k", str(out)],
            check=True,
            capture_output=True,
        )
        return out.read_bytes()
