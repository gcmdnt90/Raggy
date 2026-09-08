// Banco harness. Reads the demo database through the server; never holds
// prompt text of its own. See docs/adr/0001.
const $ = (s) => document.querySelector(s);
const state = { sector: localStorage.getItem("banco.sector") || "numismatics", demo: null };

async function boot() {
  $("#sector").textContent = state.sector;
  const demos = await (await fetch("/api/demos")).json();
  $("#demos").innerHTML = demos
    .map((d) => `<button data-id="${d.id}">${d.id.toUpperCase()} · ${d.shape}</button>`)
    .join("");
  $("#demos").addEventListener("click", (e) => {
    const id = e.target.dataset?.id;
    if (id) select(id);
  });
  if (demos.length) select(demos[0].id);
}

async function select(id) {
  state.demo = await (await fetch(`/api/demos/${id}?sector=${state.sector}`)).json();
  document.querySelectorAll("#demos button").forEach((b) =>
    b.setAttribute("aria-current", String(b.dataset.id === id)));
  const first = (state.demo.prompts || []).find((p) => p.status === "active");
  $("#prompt").textContent = first ? first.text : "";
  $("#panes").innerHTML = "";
}

// TODO(M1): run() — open an EventSource on /api/run, one .pane per model source.
//   Each event updates that pane's text and its .meta line (provider, model,
//   temperature, thinking budget, tokens) and sets #egress.
// TODO(M3): replay() — same rendering from /api/replay/{id}, with
//   #mode[data-mode="replay"] set so the room can see it is a recording.

boot();
