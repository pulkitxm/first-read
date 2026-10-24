# First Read

Hear a scene, a chat, or a changelog before you record it or ship it.

Paste what you already wrote. First Read casts a stable voice per character and performs the read with Fish Audio's drama-3 model. The same name keeps the same voice the next time you render.

## Run

```bash
python3 server.py
```

Open http://127.0.0.1:8791

Three examples play with no key: a shop scene, a support chat, and a release note. A new read bills your Fish Audio developer balance.

```bash
export FISH_API_KEY=your_key
python3 cli.py examples/counter.txt -o counter.mp3
```

Create the key under API Keys on the [developer dashboard](https://fish.audio/app/). The request sends `model: drama-3`.

## What you can paste

A screenplay. Character names in capitals, directions in parentheses.

```
INT. COUNTER - NIGHT

LENA
(quietly)
We're closed.
```

A chat.

```
Lena (quietly): We're closed.
Jun: The sign says open.
```

Or plain prose, which one narrator reads. Useful for release notes, docs, and drafts.

Pin a voice by its label when the role matters:

```
@ Lena: Sheila
@ Jun: Adrian
```

Edit `voices.json` to swap in voice ids from the Fish Audio library. Six characters plus the narrator.

```bash
python3 -m unittest
```
