import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHUNK_BYTES = 3500
INPUT_LIMIT = 12000
CAST_LIMIT = 6

SLUG = re.compile(r"^(INT\.|EXT\.|I/E\.)\s+\S", re.IGNORECASE)
CHAT = re.compile(r"^([^:\n]{1,40}?)(?:\s+\(([^)]{1,80})\))?:\s+(\S.*)$")
PIN = re.compile(r"^@\s*([^:]{1,40}?)\s*:\s*(\S.*?)\s*$")
TAG = re.compile(r"\[[^\]]*\]")
SPEAKER = re.compile(r"<\|speaker:\d+\|>")
ANGLE = re.compile(r"<[^>\n]*>")


class ScriptError(ValueError):
    pass


def load_voices(path=None):
    data = json.loads((path or ROOT / "voices.json").read_text())
    narrator = data["narrator"]
    cast = data["cast"]
    if not narrator.get("id") or len(cast) < 2:
        raise ScriptError("voices.json needs a narrator and a cast.")
    return narrator, cast


def clean_speech(text: str) -> str:
    raw = text.replace("\r", " ").replace("\n", " ")
    raw = SPEAKER.sub(" ", raw)
    raw = ANGLE.sub(" ", raw)
    raw = TAG.sub(" ", raw)
    raw = re.sub(r"\s+", " ", raw).strip().strip("\"'")
    return raw


def clean_direction(text: str) -> str:
    raw = clean_speech(text or "")
    raw = raw.strip("() ")
    raw = re.sub(r"[^a-zA-Z0-9,.' ]", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip(" ,.")
    return raw[:80]


class Cue:
    def __init__(self, name, direction, text):
        self.name = name
        self.direction = direction
        self.text = text


def _character_cue(line: str) -> bool:
    if not line or len(line) > 28 or len(line.split()) > 4:
        return False
    if line[:1] in "([":
        return False
    if line[-1:] in ".?!":
        return False
    letters = [char for char in line if char.isalpha()]
    if len(letters) < 2:
        return False
    upper = sum(1 for char in letters if char.isupper())
    return upper / len(letters) >= 0.8


def _parse_chat(text: str):
    cues = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        match = CHAT.match(line)
        if not match:
            return None
        name, direction, said = match.group(1).strip(), match.group(2), match.group(3)
        speech = clean_speech(said)
        if speech:
            cues.append(Cue(name, clean_direction(direction or ""), speech))
    return cues or None


def _parse_screenplay(text: str):
    rows = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cues = []
    index = 0
    while index < len(rows):
        line = rows[index].strip()
        if not line:
            index += 1
            continue
        if SLUG.match(line):
            cues.append(Cue("Narrator", "quiet, brief", clean_speech(line)))
            index += 1
            continue
        nxt = index + 1
        while nxt < len(rows) and not rows[nxt].strip():
            nxt += 1
        upcoming = rows[nxt].strip() if nxt < len(rows) else ""
        if _character_cue(line) and (upcoming.startswith("(") or upcoming):
            name = line.title() if line.isupper() else line
            index += 1
            direction = ""
            if index < len(rows) and rows[index].strip().startswith("("):
                direction = clean_direction(rows[index].strip().strip("()"))
                index += 1
            spoken = []
            while index < len(rows) and rows[index].strip():
                current = rows[index].strip()
                if _character_cue(current) or SLUG.match(current):
                    break
                if current.startswith("(") and current.endswith(")"):
                    extra = clean_direction(current)
                    direction = extra or direction
                else:
                    spoken.append(current)
                index += 1
            speech = clean_speech(" ".join(spoken))
            if speech:
                cues.append(Cue(name, direction, speech))
            continue
        speech = clean_speech(line)
        if speech:
            cues.append(Cue("Narrator", "quiet, brief", speech))
        index += 1
    return cues


def _parse_prose(text: str):
    speech = clean_speech(text)
    if not speech:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", speech)
    cues = []
    bucket = ""
    for sentence in sentences:
        if bucket and len(bucket) + len(sentence) > 420:
            cues.append(Cue("Narrator", "clear, steady, unhurried", bucket))
            bucket = sentence
        else:
            bucket = f"{bucket} {sentence}".strip()
    if bucket:
        cues.append(Cue("Narrator", "clear, steady, unhurried", bucket))
    return cues


def peel(text: str):
    kept = []
    pins = {}
    for raw in text.splitlines():
        match = PIN.match(raw.strip())
        if match:
            pins[match.group(1).strip().casefold()] = match.group(2).strip().casefold()
        else:
            kept.append(raw)
    return "\n".join(kept), pins


def parse(text: str):
    if not isinstance(text, str) or not text.strip():
        raise ScriptError("Paste a scene, a chat, or some prose.")
    if len(text) > INPUT_LIMIT:
        raise ScriptError("Keep a read under 12,000 characters. Split a long script into scenes.")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    chat_hits = sum(1 for line in lines if CHAT.match(line))
    if lines and chat_hits >= 2 and chat_hits >= max(1, len(lines) // 2):
        cues = _parse_chat(text)
        kind = "chat"
    elif any(_character_cue(line) or SLUG.match(line) for line in lines):
        cues = _parse_screenplay(text)
        kind = "screenplay"
    else:
        cues = _parse_prose(text)
        kind = "prose"
    cues = [cue for cue in cues if cue.text]
    if not cues:
        raise ScriptError("Nothing to read after cleaning the script.")
    return kind, cues


def assign(cues, narrator, cast, pins=None):
    chosen = {}
    pins = pins or {}
    by_label = {voice["label"].casefold(): voice for voice in [narrator, *cast]}

    def pick(name):
        key = re.sub(r"\s+", " ", name).strip()
        folded = key.casefold()
        if folded in {"narrator", "narration"}:
            return narrator
        if folded in chosen:
            return chosen[folded]
        pinned = pins.get(folded)
        if pinned:
            voice = by_label.get(pinned)
            if voice is None or voice["id"] == narrator["id"]:
                raise ScriptError(f"No cast voice named {pins[folded]}.")
            if voice["id"] in {item["id"] for item in chosen.values()}:
                raise ScriptError(f"{voice['label']} is already cast.")
            chosen[folded] = voice
            return voice
        if len(chosen) >= CAST_LIMIT:
            raise ScriptError("This read allows six characters plus the narrator.")
        start = hashlib.sha256(folded.encode()).digest()[0] % len(cast)
        taken = {voice["id"] for voice in chosen.values()}
        for offset in range(len(cast)):
            voice = cast[(start + offset) % len(cast)]
            if voice["id"] not in taken:
                chosen[folded] = voice
                return voice
        raise ScriptError("This read allows six characters plus the narrator.")

    rows = []
    for cue in cues:
        voice = pick(cue.name)
        rows.append(
            {
                "name": cue.name if cue.name.casefold() != "narrator" else "Narrator",
                "direction": cue.direction,
                "text": cue.text,
                "voice_id": voice["id"],
                "voice": voice["label"],
            }
        )
    return rows


def encode(rows):
    chunks = []
    current = []
    size = 0
    for row in rows:
        direction = f"[{row['direction']}] " if row["direction"] else ""
        piece = f"{direction}{row['text']}"
        extra = len(piece.encode()) + 20
        if current and size + extra > CHUNK_BYTES:
            chunks.append(_encode_chunk(current))
            current = []
            size = 0
        current.append({**row, "piece": piece})
        size += extra
    if current:
        chunks.append(_encode_chunk(current))
    return chunks


def _encode_chunk(rows):
    order = []
    parts = []
    for row in rows:
        if row["voice_id"] not in order:
            order.append(row["voice_id"])
        index = order.index(row["voice_id"])
        parts.append(f"<|speaker:{index}|>{row['piece']}")
    return {"text": "".join(parts), "voice_ids": order}


def prepare(text: str, voices_path=None):
    narrator, cast = load_voices(voices_path)
    body, pins = peel(text)
    kind, cues = parse(body)
    rows = assign(cues, narrator, cast, pins)
    cast_list = []
    seen = set()
    for row in rows:
        if row["name"] in seen:
            continue
        seen.add(row["name"])
        cast_list.append({"name": row["name"], "voice": row["voice"]})
    return {
        "kind": kind,
        "lines": [{"name": row["name"], "direction": row["direction"], "text": row["text"], "voice": row["voice"]} for row in rows],
        "cast": cast_list,
        "chunks": encode(rows),
    }
