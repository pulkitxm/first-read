const examplesEl = document.querySelector("#examples");
const scriptEl = document.querySelector("#script");
const form = document.querySelector("#desk");
const statusEl = document.querySelector("#status");
const stage = document.querySelector("#stage");
const kindEl = document.querySelector("#kind");
const castEl = document.querySelector("#cast");
const linesEl = document.querySelector("#lines");
const player = document.querySelector("#player");
const download = document.querySelector("#download");

let objectUrl = null;
let examples = [];

function setStatus(text) {
  statusEl.textContent = text || "";
}

function show(read, audioUrl) {
  kindEl.textContent = read.topic ? `${read.kind} · ${read.topic}` : read.kind;
  castEl.replaceChildren();
  for (const person of read.cast) {
    const item = document.createElement("li");
    item.textContent = `${person.name} · ${person.voice}`;
    castEl.append(item);
  }
  linesEl.replaceChildren();
  for (const line of read.lines) {
    const item = document.createElement("li");
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = line.direction ? `${line.name} (${line.direction})` : line.name;
    const said = document.createElement("span");
    said.textContent = line.text;
    item.append(name, said);
    linesEl.append(item);
  }
  if (objectUrl && objectUrl !== audioUrl) {
    URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }
  if (!audioUrl) {
    player.removeAttribute("src");
    player.hidden = true;
    download.hidden = true;
  } else {
    player.hidden = false;
    download.hidden = false;
    player.src = audioUrl;
    download.href = audioUrl;
    player.play().catch(() => {});
  }
  stage.hidden = false;
  stage.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function loadExample(example) {
  scriptEl.value = example.script;
  if (example.audio) show(example, example.audio);
}

fetch("/api/examples")
  .then((response) => response.json())
  .then((payload) => {
    examples = payload.examples;
    for (const example of examples) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = example.title;
      button.addEventListener("click", () => loadExample(example));
      examplesEl.append(button);
    }
  })
  .catch(() => setStatus("Examples did not load."));

const topicEl = document.querySelector("#topic");
const debateStatus = document.querySelector("#debate-status");
const topicsEl = document.querySelector("#topics");
let speakers = 2;
let extraRounds = 0;

function setDebateStatus(text) {
  debateStatus.textContent = text || "";
}

for (const button of document.querySelectorAll("#speaker-count button")) {
  button.addEventListener("click", () => {
    speakers = Number(button.dataset.speakers);
    extraRounds = 0;
    for (const other of document.querySelectorAll("#speaker-count button")) {
      other.setAttribute("aria-pressed", String(other === button));
    }
  });
}

async function runDebate() {
  const topic = topicEl.value.trim();
  if (!topic) {
    setDebateStatus("Give it a topic.");
    return;
  }
  const go = document.querySelector("#debate-go");
  go.disabled = true;
  setDebateStatus("They are taking their seats.");
  try {
    const response = await fetch("/api/debate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, speakers, extra_rounds: extraRounds }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setDebateStatus(payload.error || "The debate failed.");
      return;
    }
    scriptEl.value = payload.script || "";
    if (payload.audio) {
      show(payload, payload.audio);
      setDebateStatus("");
    } else if (payload.audio_base64) {
      const bytes = Uint8Array.from(atob(payload.audio_base64), (char) => char.charCodeAt(0));
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));
      show(payload, objectUrl);
      setDebateStatus("");
    } else {
      show(payload, null);
      setDebateStatus(payload.note || "The script is ready. Add FISH_API_KEY to hear a topic that is not recorded yet.");
    }
  } catch (error) {
    setDebateStatus("The debate failed.");
  } finally {
    go.disabled = false;
  }
}

document.querySelector("#debate-form").addEventListener("submit", (event) => {
  event.preventDefault();
  extraRounds = 0;
  runDebate();
});

document.querySelector("#debate-more").addEventListener("click", () => {
  extraRounds += 1;
  runDebate();
});

fetch("/api/debates")
  .then((response) => response.json())
  .then((payload) => {
    for (const debate of payload.debates) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = debate.topic;
      button.addEventListener("click", () => {
        topicEl.value = debate.topic;
        speakers = debate.speakers;
        extraRounds = 0;
        for (const other of document.querySelectorAll("#speaker-count button")) {
          other.setAttribute("aria-pressed", String(Number(other.dataset.speakers) === speakers));
        }
        runDebate();
      });
      topicsEl.append(button);
    }
  })
  .catch(() => setDebateStatus("Topics did not load."));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const go = document.querySelector("#go");
  go.disabled = true;
  setStatus("Reading.");
  try {
    const response = await fetch("/api/read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ script: scriptEl.value }),
    });
    const payload = await response.json();
    if (!response.ok) {
      setStatus(payload.error || "The read failed.");
      return;
    }
    const bytes = Uint8Array.from(atob(payload.audio_base64), (char) => char.charCodeAt(0));
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(new Blob([bytes], { type: "audio/mpeg" }));
    show(payload, objectUrl);
    setStatus("");
  } catch (error) {
    setStatus("The read failed.");
  } finally {
    go.disabled = false;
  }
});
