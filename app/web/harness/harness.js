// Banco harness. Reads the demo database through the server; never holds prompt
// text of its own (docs/adr/0001), and never renders output no model produced
// (AGENTS.md rule 1) — an unavailable pane shows its reason, not a placeholder.
const $ = (s) => document.querySelector(s);
const el = (tag, cls) => Object.assign(document.createElement(tag), cls ? { className: cls } : {});

const state = {
  sector: localStorage.getItem("banco.sector") || "numismatics",
  demoId: null,
  demo: null,
  beatId: null,
  running: false,
  egress: new Map(), // target -> local?  kept for the whole session, not per run
};

// ── boot ───────────────────────────────────────────────────────────────────

async function boot() {
  const [status, sectorList, demos] = await Promise.all([
    json("/api/status"),
    json("/api/sectors"),
    json("/api/demos"),
  ]);

  renderProfile(status);
  renderSectors(sectorList);
  renderDemos(demos);

  if (demos.length) selectDemo(state.demoId && demos.some(d => d.id === state.demoId)
    ? state.demoId : demos[0].id);
}

async function json(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return res.json();
}

function renderProfile(status) {
  const roles = Object.entries(status.roles || {});
  $("#profile").textContent = status.profile;
  $("#profile").dataset.profile = status.profile;
  $("#profile").title = roles.length
    ? roles.map(([r, s]) => `${r}: ${s.provider} ${s.model} → ${s.egress}`).join("\n")
    : "no model source configured";
}

function renderSectors(list) {
  const sel = $("#sector");
  sel.innerHTML = "";
  for (const s of list) {
    const opt = el("option");
    opt.value = s.id;
    opt.textContent = s.label || s.id;
    sel.append(opt);
  }
  sel.value = state.sector;
  sel.addEventListener("change", () => {
    state.sector = sel.value;
    localStorage.setItem("banco.sector", state.sector);
    if (state.demoId) selectDemo(state.demoId);
  });
}

function renderDemos(demos) {
  const nav = $("#demos");
  nav.innerHTML = "";
  for (const d of demos) {
    const b = el("button");
    b.dataset.id = d.id;
    b.innerHTML = `<strong>${d.id.toUpperCase()}</strong><span>${d.shape}</span>`;
    b.addEventListener("click", () => selectDemo(d.id));
    nav.append(b);
  }
}

// ── selection ──────────────────────────────────────────────────────────────

async function selectDemo(id) {
  state.demoId = id;
  state.demo = await json(`/api/demos/${id}?sector=${encodeURIComponent(state.sector)}`);
  document.querySelectorAll("#demos button").forEach((b) =>
    b.setAttribute("aria-current", String(b.dataset.id === id)));

  const list = $("#beats");
  list.innerHTML = "";
  for (const beat of state.demo.prompts || []) {
    const li = el("li", beat.run.runnable ? "runnable" : "blocked-beat");
    li.dataset.id = beat.id;
    li.innerHTML =
      `<span class="beat-id">${beat.id}</span>` +
      `<span class="beat-label">${escapeHtml(beat.label || "")}</span>` +
      (beat.run.runnable
        ? `<span class="beat-panes">${beat.run.panes} panes</span>`
        : `<span class="beat-panes">—</span>`);
    li.addEventListener("click", () => selectBeat(beat.id));
    list.append(li);
  }

  const firstRunnable = (state.demo.prompts || []).find((p) => p.run.runnable);
  if (firstRunnable) selectBeat(firstRunnable.id);
  else { $("#detail").hidden = true; $("#panes").innerHTML = ""; }
}

function beatById(id) {
  return (state.demo.prompts || []).find((p) => p.id === id);
}

function selectBeat(id) {
  state.beatId = id;
  const beat = beatById(id);
  document.querySelectorAll("#beats li").forEach((li) =>
    li.setAttribute("aria-current", String(li.dataset.id === id)));

  $("#detail").hidden = false;
  $("#teaches").textContent = beat.run.teaches || "";
  $("#prompt").textContent = beat.text || "";
  $("#prompt-box").hidden = false;

  const blocked = $("#blocked");
  blocked.hidden = beat.run.runnable;
  blocked.textContent = beat.run.runnable ? "" : (beat.run.reason || "not executable");

  $("#run").disabled = !beat.run.runnable || state.running;
  $("#run").textContent = beat.run.continues
    ? `Run — continues ${beat.run.continues}`
    : "Run";

  $("#panes").innerHTML = "";
  $("#banner").hidden = true;
}

// ── running ────────────────────────────────────────────────────────────────

$("#run").addEventListener("click", run);

async function run() {
  if (state.running || !state.beatId) return;
  state.running = true;
  $("#run").disabled = true;
  $("#banner").hidden = true;

  try {
    const res = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        demo_id: state.demoId,
        beat_id: state.beatId,
        sector: state.sector,
      }),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      showBanner(detail.detail || `run refused (${res.status})`, "error");
      return;
    }

    for await (const ev of readEvents(res)) handleEvent(ev);
  } catch (err) {
    showBanner(String(err), "error");
  } finally {
    state.running = false;
    $("#run").disabled = false;
  }
}

// Minimal SSE reader over fetch. EventSource cannot POST, and the request
// carries a body, so the framing is parsed here: events are separated by a
// blank line, and each has an `event:` and a single-line `data:`.
async function* readEvents(res) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let split;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      let name = "message";
      let data = "{}";
      for (const line of raw.split("\n")) {
        if (line.startsWith("event: ")) name = line.slice(7).trim();
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      yield { name, data: JSON.parse(data) };
    }
  }
}

function handleEvent({ name, data }) {
  switch (name) {
    case "plan": return onPlan(data);
    case "delta": return onDelta(data);
    case "pane_done": return onPaneDone(data);
    case "pane_failed": return onPaneFailed(data);
    case "pane_unavailable": return onPaneUnavailable(data);
    case "chain_failed":
      return showBanner(`chain file not written: ${data.error}`, "error");
    case "run_done": return onRunDone(data);
  }
}

function onPlan(plan) {
  $("#prompt").textContent = plan.prompt;      // the prompt as actually sent
  // Live is announced as loudly as replay. If only replay were labelled, a
  // room would have to notice an absence to know what it is watching.
  const mode = $("#mode");
  mode.hidden = false;
  mode.dataset.mode = plan.replayed ? "replay" : "live";
  mode.textContent = plan.replayed ? "REPLAY — a recording of a real run" : "LIVE";

  const host = $("#panes");
  host.innerHTML = "";
  host.dataset.count = plan.panes.length;

  for (const pane of plan.panes) {
    const card = el("article", "pane");
    card.dataset.pane = pane.pane;
    card.innerHTML =
      `<header>` +
        `<span class="pane-label">${escapeHtml(pane.label)}</span>` +
        `<span class="pane-state" data-state="waiting">waiting</span>` +
      `</header>` +
      `<div class="meta mono">${paneMeta(pane)}</div>` +
      `<div class="out"></div>`;
    host.append(card);
  }

  if (plan.degraded) {
    showBanner(
      "Degraded: not every pane has a model source. Unavailable panes are marked, " +
      "never filled in.",
      "warn"
    );
  }
}

// Provider, model, temperature, thinking budget and destination — the mechanism
// this whole application exists to put on a screen (PROJECT.md objective 2).
function paneMeta(pane) {
  if (pane.unavailable) return `<span class="unavailable">unavailable</span>`;
  const bits = [`${escapeHtml(pane.provider)} · ${escapeHtml(pane.model)}`];
  // Never state a temperature the model discards: Anthropic dropped sampling
  // parameters after Opus 4.6, and a false number here is worse than none.
  bits.push(pane.temperature_applies === false
    ? `<span class="unavailable">temp ${pane.temperature} not honoured by this model</span>`
    : `temp ${pane.temperature}`);
  if (pane.thinking) bits.push(`thinking ${escapeHtml(pane.thinking)}`);
  bits.push(
    `<span class="target ${pane.local ? "local" : "remote"}">` +
    `${pane.local ? "local" : "→"} ${escapeHtml(pane.egress)}</span>`
  );
  return bits.join(" <span class=sep>|</span> ");
}

function pane(i) { return document.querySelector(`.pane[data-pane="${i}"]`); }
function setState(i, text, value) {
  const node = pane(i)?.querySelector(".pane-state");
  if (node) { node.textContent = text; node.dataset.state = value; }
}

function onDelta({ pane: i, text }) {
  const out = pane(i)?.querySelector(".out");
  if (!out) return;
  out.textContent += text;
  setState(i, "streaming", "streaming");
  out.scrollTop = out.scrollHeight;
}

function onPaneDone({ pane: i, egress, local }) {
  setState(i, "done", "done");
  noteEgress(egress, local);
}

function onPaneFailed({ pane: i, error }) {
  setState(i, "failed", "failed");
  const out = pane(i)?.querySelector(".out");
  if (out) {
    const p = el("p", "failure");
    p.textContent = error;   // narrated, not hidden
    out.append(p);
  }
}

function onPaneUnavailable({ pane: i, reason, recording }) {
  setState(i, "unavailable", "unavailable");
  const out = pane(i)?.querySelector(".out");
  if (!out) return;
  const p = el("p", "failure");
  p.textContent = recording
    ? `${reason} — replaying a recording`
    : `${reason}. No recording exists yet, so nothing is shown here rather than something invented.`;
  out.append(p);
}

function onRunDone(done) {
  if (done.produced) showBanner(`chain file written: ${done.produced}`, "ok");
  else if (done.chain_held)
    showBanner(
      "Chain file left untouched: not every pane succeeded, so the version that " +
      "shipped is still in place.",
      "warn"
    );
}

function noteEgress(target, local) {
  if (!target) return;
  state.egress.set(target, local);

  const entries = [...state.egress];
  $("#egress-targets").innerHTML = entries
    .map(([t, isLocal]) =>
      `<span class="target ${isLocal ? "local" : "remote"}">${escapeHtml(t)}</span>`)
    .join(" ");

  // One word for the whole run, because that is what the room is asked about in
  // D5-A: did anything leave this machine? "mixed" is the honest answer when
  // some panes were local and some were not, and it must not read as "local".
  const anyRemote = entries.some(([, isLocal]) => !isLocal);
  const anyLocal = entries.some(([, isLocal]) => isLocal);
  $("#egress").dataset.where = anyRemote && anyLocal ? "mixed" : anyRemote ? "remote" : "local";
}

function showBanner(text, kind) {
  const b = $("#banner");
  b.textContent = text;
  b.dataset.kind = kind;
  b.hidden = false;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

boot().catch((err) => showBanner(`cannot reach the server: ${err}`, "error"));
