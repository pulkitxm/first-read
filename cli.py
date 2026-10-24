#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from fish import load_env, speak_chunks
from readthrough import ScriptError, prepare

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Render a scene, a chat, or prose with Fish Audio.")
    parser.add_argument("script", type=Path, help="Text file to read")
    parser.add_argument("-o", "--output", type=Path, required=True, help="mp3 to write")
    args = parser.parse_args()
    load_env(ROOT)
    try:
        read = prepare(args.script.read_text())
        audio = speak_chunks(read["chunks"])
    except (ScriptError, RuntimeError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    args.output.write_bytes(audio)
    names = ", ".join(f"{row['name']} ({row['voice']})" for row in read["cast"])
    print(f"{read['kind']}: {names}")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
