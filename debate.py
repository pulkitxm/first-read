import re

from readthrough import ScriptError, prepare

ROLES = {
    "Mira": "Sheila",
    "Owen": "Adrian",
    "Priya": "Clear Speaker",
}

PRESETS = [
    {
        "id": "remote",
        "topic": "Should remote work be the default?",
        "speakers": 2,
        "turns": [
            ("Mira", "steady, opening", "Remote as the default means the office is a tool, not a test of loyalty. Judge the work."),
            ("Owen", "pushing back", "The work that is a conversation gets worse. I have sat in calls where five people talk and nobody decides."),
            ("Mira", "firmer", "Then decide in the document before the call. The office did not make those meetings good. It only made them harder to leave."),
            ("Owen", "insisting", "New hires still learn by hearing how a decision actually sounds. A document does not carry that."),
            ("Mira", "conceding a piece", "Give them one week a month in the room. Not four days a week of badge checks."),
            ("Owen", "closing, calmer", "One week, planned, with a reason. I will take that. I will not take never come in as the default."),
        ],
    },
    {
        "id": "tabs",
        "topic": "Tabs or spaces?",
        "speakers": 2,
        "turns": [
            ("Mira", "plain, sure", "Spaces. The file should look the same on every machine without a setting."),
            ("Owen", "quick, enjoying it", "Tabs. One character for one level, and the reader picks the width. Spaces bake your taste into the diff."),
            ("Mira", "sharper", "The diff is the point. A tab and a space in one file is how a two-line change becomes two hundred lines."),
            ("Owen", "shrugging", "That is a formatter's job. Arguing the character is how a team avoids picking a formatter."),
            ("Mira", "landing it", "Then the formatter is the decision. I want it to write spaces, so a raw file is still readable in a pager."),
            ("Owen", "closing, stubborn", "Tabs in the file, width on the screen. I will die on the diff staying small."),
        ],
    },
    {
        "id": "phones",
        "topic": "Should phones be banned in class?",
        "speakers": 3,
        "turns": [
            ("Mira", "firm, opening", "Ban them in class. A pocket full of notifications is not a neutral object on a desk."),
            ("Owen", "objecting", "A ban is a cop. The student who needs a phone for a parent or a health alert gets punished with everyone else."),
            ("Priya", "cutting in, practical", "Lock them for the lesson, not the day. A pouch until the bell, and a desk in the office for the real exceptions."),
            ("Mira", "pressing", "Pouches fail when nobody checks. A rule that is not enforced is a suggestion the loudest kid ignores."),
            ("Owen", "holding the line", "A hard ban teaches them to hide the phone better. I would rather teach the moment it is supposed to be closed."),
            ("Priya", "closing, settling it", "Then grade the closed part. Phones in the pouch, exceptions written down, and the lesson starts on time. Argue the check, not the slogan."),
        ],
    },
    {
        "id": "week",
        "topic": "Is a four-day week better?",
        "speakers": 2,
        "turns": [
            ("Mira", "hopeful, concrete", "Four days. The fifth is already full of meetings that exist because the week is long."),
            ("Owen", "wary", "Four days often means ten-hour days. Parents do not get a gift if Thursday ends at seven."),
            ("Mira", "correcting", "Then do not stretch the day. Cut the standing meetings and keep the hours. Fewer days on, not longer ones."),
            ("Owen", "naming the cost", "Clients still call on Friday. Someone covers, and that someone starts to resent the policy."),
            ("Mira", "offering the fix", "Rotate the cover and publish it. A quiet Friday for most of the team is worth a listed shift."),
            ("Owen", "closing, conditional", "I will try it for a quarter. If the cover list turns into the same three people, we stop."),
        ],
    },
]


def clean_topic(topic: str) -> str:
    if not isinstance(topic, str):
        raise ScriptError("Give the debate a topic.")
    raw = re.sub(r"\s+", " ", topic).strip().strip("\"'")
    raw = re.sub(r"<[^>\n]*>", "", raw)
    raw = re.sub(r"\[[^\]]*\]", "", raw).strip()
    if not raw:
        raise ScriptError("Give the debate a topic.")
    if len(raw) > 90:
        raw = raw[:90].rsplit(" ", 1)[0].rstrip(",.;:") or raw[:90]
    if raw[-1:] not in ".?":
        raw = raw if raw.endswith("?") else raw
    return raw


def spoken_topic(topic: str) -> str:
    text = topic.strip()
    if text[-1:] not in ".?":
        text += "."
    return text


def match_preset(topic: str):
    folded = topic.casefold().strip(" ?.")
    for preset in PRESETS:
        name = preset["topic"].casefold().strip(" ?.")
        if folded == name or folded == preset["id"]:
            return preset
    return None


def template_turns(topic: str, speakers: int, rounds: int):
    question = spoken_topic(topic)
    bank = [
        [
            ("Mira", "opening, steady", f"Here is the question. {question} I want a real change, with a date, and a list of what we stop doing."),
            ("Owen", "skeptical, quick", "I want the opposite. It looks clean as a sentence and sloppy the week you run it. The people who like it are not the ones who clean up the exception."),
            ("Priya", "cutting in", "You are both holding one switch. Change the part that can travel. Leave the part that needs a person in the room."),
        ],
        [
            ("Mira", "pressing", "You keep saying exception as if that ends it. Name a cost that is worse than another year of the same habit."),
            ("Owen", "concrete", "Time. The first month becomes meetings about the rule. I have watched a team do that and call it progress."),
            ("Priya", "practical", "Then the rule has to fit on a card. If it needs a committee, Owen is right. If it fits on a card, Mira is right."),
        ],
        [
            ("Mira", "offering", "A card, then. One page, a start date, and a way to undo it in thirty days. That is a trial, not a leap."),
            ("Owen", "warning", "Undo is the part people forget. Once a team rearranges around it, going back is a second project."),
            ("Priya", "insisting", "So the old way stays on the calendar. Not in a footnote. If the undo is fiction, do not start."),
        ],
        [
            ("Mira", "closing", "I can live with a dated trial. I cannot live with another year of only talking about it."),
            ("Owen", "closing, calmer", "I can live with a trial. I will not let anyone call the trial the new default on day one."),
            ("Priya", "closing, settling", "Then argue the date and the undo. Not the fantasy of a perfect rule."),
        ],
    ]
    turns = []
    for index in range(rounds):
        for name, direction, line in bank[index % len(bank)]:
            if speakers == 2 and name == "Priya":
                continue
            turns.append((name, direction, line if index < len(bank) else line))
    return turns


def turns_for(topic: str, speakers: int, extra_rounds: int = 0):
    if speakers not in (2, 3):
        raise ScriptError("Pick two or three voices.")
    if extra_rounds < 0 or extra_rounds > 4:
        raise ScriptError("Keep the extra rounds small.")
    preset = match_preset(topic)
    if preset and extra_rounds == 0 and speakers == preset["speakers"]:
        return preset["turns"], preset
    base = preset["turns"] if preset and speakers == preset["speakers"] else template_turns(topic, speakers, 4)
    if speakers == 3 and preset and preset["speakers"] == 2:
        base = template_turns(topic, 3, 4)
    extra = template_turns(topic, speakers, extra_rounds) if extra_rounds else []
    if extra_rounds and preset and speakers == preset["speakers"]:
        return list(preset["turns"]) + extra, preset
    if preset and speakers == preset["speakers"]:
        return base, preset
    return template_turns(topic, speakers, 4 + extra_rounds), None


def script_for(turns):
    lines = [f"@ {name}: {ROLES[name]}" for name in ROLES if any(turn[0] == name for turn in turns)]
    lines.append("")
    for name, direction, text in turns:
        lines.append(f"{name} ({direction}): {text}")
    return "\n".join(lines)


def build_debate(topic: str, speakers: int = 2, extra_rounds: int = 0):
    cleaned = clean_topic(topic)
    turns, preset = turns_for(cleaned, speakers, extra_rounds)
    if preset and extra_rounds == 0 and speakers == preset["speakers"]:
        title = preset["topic"]
    else:
        title = cleaned
    read = prepare(script_for(turns))
    return {
        "id": preset["id"] if preset else None,
        "topic": title,
        "speakers": speakers,
        "preset": bool(preset) and extra_rounds == 0 and speakers == (preset["speakers"] if preset else speakers),
        "script": script_for(turns),
        "kind": "debate",
        "lines": read["lines"],
        "cast": read["cast"],
        "chunks": read["chunks"],
    }


def preset_cards():
    return [
        {"id": preset["id"], "topic": preset["topic"], "speakers": preset["speakers"]}
        for preset in PRESETS
    ]
