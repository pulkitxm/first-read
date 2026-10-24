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
  kindEl.textContent = read.kind;
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
  player.src = audioUrl;
  download.href = audioUrl;
  stage.hidden = false;
  player.play().catch(() => {});
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
    if (examples[0]) loadExample(examples[0]);
  })
  .catch(() => setStatus("Examples did not load."));

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
