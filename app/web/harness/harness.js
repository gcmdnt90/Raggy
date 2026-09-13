// Banco harness. Reads the demo database through the server; never holds prompt
// text of its own (docs/adr/0001), and never renders output no model produced
// (AGENTS.md rule 1) — an unavailable pane shows its reason, not a placeholder.
//
// Two kinds of text arrive here and they are handled differently. Banco's own
// words — labels, states, banners — come from `i18n.t` or, when the server
// composed them, already translated by app/i18n.py. Words from the demo
// database are picked per language by `pick()`, which knows the `_it`
// convention. Model output is never touched.
const $ = (s) => document.querySelector(s);
const el = (tag, cls) => Object.assign(document.createElement(tag), cls ? { className: cls } : {});
const t = (key, vars) => i18n.t(key, vars);

const state = {
  sector: localStorage.getItem("banco.sector") || "numismatics",
  demoId: null,
  demo: null,
  beatId: null,
  running: false,
  egress: new Map(), // target -> local?  kept for the whole session, not per run
  // What each beat produced, kept for the whole session and keyed by beat id.
  // A lesson is not a straight line: the trainer goes back to D1 to point at a
  // field, then forward to D3, and before this the panes were wiped on the way
  // out. Re-running to get them back costs money, costs time in front of a
  // room, and — since nothing is deterministic — comes back a different answer,
  // so the thing being pointed at is gone. Nothing here is replayed or
  // re-generated: it is the same DOM the run built, put back (invariant 2).
  results: new Map(), // beat id -> { panes: innerHTML, mode: {...}, banner: {...} }
  showAllBeats: false,
  // Prompts the trainer edited in the viewer, by beat id. For this session
  // only, and never written back to the demo database (ADR 0001).
  promptEdits: new Map(),
  // Role -> { provider, model, think } chosen at the gear. Roles, not panes.
  overrides: {},
  catalogue: null,
};

// The demo database is bilingual by field suffix: `label` is English, `label_it`
// is Italian. One function knows that, here and in app/i18n.py, and nothing else
// concatenates "_it" onto a field name.
function pick(node, field) {
  if (!node) return "";
  const localized = i18n.lang === "it" ? node[`${field}_it`] : node[field];
  return localized || node[field] || "";
}

// ── boot ───────────────────────────────────────────────────────────────────

async function boot() {
  await load();
}

// Re-entrant: also the language-change path. `keepPanes` is what makes changing
// language mid-lesson safe — the chrome and the labels are rebuilt, the output
// four models have already produced stays on screen.
async function load({ keepPanes = false } = {}) {
  const [status, sectorList, demos] = await Promise.all([
    json("/api/status"),
    json("/api/sectors"),
    json("/api/demos"),
  ]);

  renderProfile(status);
  renderSectors(sectorList);
  renderDemos(demos);

  if (!demos.length) return;
  const wanted = state.demoId && demos.some((d) => d.id === state.demoId)
    ? state.demoId
    : demos[0].id;
  await selectDemo(wanted, { keepPanes });
}

async function json(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return res.json();
}

// Every request that can come back with server-composed text says which
// language it wants. There is no session: the language is the browser's.
function withLang(url) {
  return `${url}${url.includes("?") ? "&" : "?"}lang=${encodeURIComponent(i18n.lang)}`;
}

function renderProfile(status) {
  const roles = Object.entries(status.roles || {});
  $("#profile").textContent = status.profile;
  $("#profile").dataset.profile = status.profile;
  $("#profile").title = roles.length
    ? roles.map(([r, s]) => `${r}: ${s.provider} ${s.model} → ${s.egress}`).join("\n")
    : t("harness.no_source_configured");
}

function renderSectors(list) {
  const sel = $("#sector");
  sel.innerHTML = "";
  for (const s of list) {
    const opt = el("option");
    opt.value = s.id;
    opt.textContent = pick(s, "label") || s.id;
    sel.append(opt);
  }
  sel.value = state.sector;
  sel.onchange = () => {
    state.sector = sel.value;
    localStorage.setItem("banco.sector", state.sector);
    if (state.demoId) selectDemo(state.demoId);
  };
}

function renderDemos(demos) {
  const nav = $("#demos");
  nav.innerHTML = "";
  for (const d of demos) {
    const b = el("button");
    b.dataset.id = d.id;
    b.title = pick(d, "title");
    b.innerHTML =
      `<strong>${escapeHtml(String(d.id).toUpperCase())}</strong>` +
      `<span>${escapeHtml(pick(d, "shape"))}</span>`;
    b.addEventListener("click", () => selectDemo(d.id));
    nav.append(b);
  }
  if (state.demoId) markDemo(state.demoId);
}

// ── selection ──────────────────────────────────────────────────────────────

function markDemo(id) {
  document.querySelectorAll("#demos button").forEach((b) =>
    b.setAttribute("aria-current", String(b.dataset.id === id)));
}

async function selectDemo(id, { keepPanes = false } = {}) {
  state.demoId = id;
  // `teaches` and a blocked beat's reason are composed by the server from
  // run-blocks.json, so the language goes with the request.
  state.demo = await json(
    withLang(`/api/demos/${id}?sector=${encodeURIComponent(state.sector)}`));
  markDemo(id);

  const list = $("#beats");
  list.innerHTML = "";
  // Only the beats Banco can actually run, unless the trainer asks for the
  // rest. The database declares thirty-two and eight have run blocks; a
  // projected list where three quarters of the rows cannot be pressed is a
  // list the room reads as broken. Nothing is deleted and nothing is hidden
  // from the console — AGENTS.md rule 7 keeps every archived beat on purpose,
  // and the toggle below is how you reach them.
  const all = state.demo.prompts || [];
  const shown = state.showAllBeats ? all : all.filter((p) => p.run.runnable);
  for (const beat of shown) {
    const li = el("li", beat.run.runnable ? "runnable" : "blocked-beat");
    li.dataset.id = beat.id;
    if (state.results.has(beat.id)) li.classList.add("has-result");
    li.innerHTML =
      `<span class="beat-id">${escapeHtml(beat.id)}</span>` +
      `<span class="beat-label">${escapeHtml(pick(beat, "label"))}</span>` +
      `<span class="beat-panes">${escapeHtml(beat.run.runnable
        ? t("harness.beat_panes", { count: beat.run.panes })
        : t("harness.beat_no_panes"))}</span>`;
    li.addEventListener("click", () => selectBeat(beat.id));
    list.append(li);
  }

  const hiddenCount = all.length - shown.length;
  if (hiddenCount || state.showAllBeats) {
    const toggle = el("li", "beats-toggle");
    toggle.innerHTML = `<button type="button">${escapeHtml(
      state.showAllBeats
        ? t("harness.beats_show_runnable")
        : t("harness.beats_show_all", { count: hiddenCount }))}</button>`;
    toggle.addEventListener("click", () => {
      state.showAllBeats = !state.showAllBeats;
      selectDemo(state.demoId, { keepPanes: true });
    });
    list.append(toggle);
  }

  const wanted = state.beatId && beatById(state.beatId)
    ? state.beatId
    : shown.find((p) => p.run.runnable)?.id || all.find((p) => p.run.runnable)?.id;

  if (wanted) selectBeat(wanted, { keepPanes });
  else { $("#detail").hidden = true; if (!keepPanes) $("#panes").innerHTML = ""; }
}

function beatById(id) {
  return (state.demo.prompts || []).find((p) => p.id === id);
}

function selectBeat(id, { keepPanes = false } = {}) {
  const beat = beatById(id);
  if (!beat) return;
  // Snapshot what is on screen before leaving it, so a beat mid-stream is kept
  // as far as it got rather than only beats that finished.
  if (state.beatId && state.beatId !== id) rememberResult(state.beatId);
  state.beatId = id;
  document.querySelectorAll("#beats li").forEach((li) =>
    li.setAttribute("aria-current", String(li.dataset.id === id)));

  $("#detail").hidden = false;
  $("#teaches").textContent = beat.run.teaches || "";
  // `beat.run.prompt` and never `beat.text`: the bare field is the English one
  // (the `_it` suffix is what `pick` knows about), and it is the template, with
  // the paste placeholder still in it. Both halves showed on a projected screen
  // under a label that says "as sent". The server composes this now.
  $("#prompt").textContent = beat.run.prompt || "";
  setPromptSummary(beat.run.prompt_complete);
  $("#prompt-box").hidden = false;

  const blocked = $("#blocked");
  blocked.hidden = beat.run.runnable;
  blocked.textContent = beat.run.runnable
    ? ""
    : (beat.run.reason || t("harness.not_executable"));

  $("#run").disabled = !beat.run.runnable || state.running;
  $("#run").textContent = beat.run.continues
    ? t("harness.run_continues", { beat: beat.run.continues })
    : t("harness.run");

  if (keepPanes) return;
  restoreResult(id);
}

// ── what a beat produced, kept for the session ─────────────────────────────
//
// The stored value is the DOM the run itself built, nothing more. It is never
// re-requested and never re-generated: putting back a *different* answer under
// the same beat would be Banco showing output that no model produced for this
// pane, which invariant 2 forbids as firmly as inventing one.

function rememberResult(beatId) {
  const host = $("#panes");
  if (!host.innerHTML.trim()) return;
  const mode = $("#mode");
  const banner = $("#banner");
  state.results.set(beatId, {
    panes: host.innerHTML,
    count: host.dataset.count || "",
    mode: mode.hidden ? null : { text: mode.textContent, kind: mode.dataset.mode },
    banner: banner.hidden ? null : { text: banner.textContent, kind: banner.dataset.kind },
  });
}

function restoreResult(beatId) {
  const host = $("#panes");
  const mode = $("#mode");
  const banner = $("#banner");
  const saved = state.results.get(beatId);

  host.innerHTML = saved ? saved.panes : "";
  host.dataset.count = saved ? saved.count : "";

  mode.hidden = !(saved && saved.mode);
  if (saved && saved.mode) {
    mode.textContent = saved.mode.text;
    mode.dataset.mode = saved.mode.kind;
  }

  banner.hidden = !(saved && saved.banner);
  if (saved && saved.banner) {
    banner.textContent = saved.banner.text;
    banner.dataset.kind = saved.banner.kind;
  }

  $("#reset-run").hidden = !saved;
}

// Explicit, and only ever for the beat in front of you. A control that cleared
// every beat at once is one mis-click away from throwing out a demonstration
// the room has not finished discussing.
function resetCurrentResult() {
  if (!state.beatId || state.running) return;
  state.results.delete(state.beatId);
  restoreResult(state.beatId);
  document.querySelectorAll("#beats li").forEach((li) =>
    li.classList.toggle("has-result", state.results.has(li.dataset.id)));
}

// The panel's label is a claim about the text under it, so it follows the text.
// `data-i18n` is rewritten rather than bypassed: the language switch rebuilds
// every marked node from the catalogue, and a label set only here would be
// replaced by whichever key the markup still carried.
function setPromptSummary(complete) {
  // An edited prompt gets its own label. "Come inviato" would still be true of
  // the text, but it reads as "this is what the deck says", and a prompt the
  // room cannot trace to the slides has to announce itself — that was the whole
  // condition on making it editable at all.
  const key = state.promptEdits.has(state.beatId)
    ? "harness.prompt_summary_edited"
    : complete ? "harness.prompt_summary" : "harness.prompt_summary_template";
  const summary = $("#prompt-summary");
  if (!summary) return;
  summary.dataset.i18n = key;
  summary.textContent = t(key);
}

// ── language ───────────────────────────────────────────────────────────────

// i18n.js has already re-written every `data-i18n` node by the time this fires;
// what is left is everything JavaScript built, plus the server-composed text
// that has to be fetched again in the new language.
addEventListener(i18n.EVENT, () => {
  load({ keepPanes: true }).catch((err) =>
    showBanner(t("harness.server_unreachable", { error: String(err) }), "error"));
});

// ── running ────────────────────────────────────────────────────────────────

$("#run").addEventListener("click", run);
$("#reset-run").addEventListener("click", resetCurrentResult);

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
        // The prompt itself has an Italian and an English text in the demo
        // database. This is what decides which one is sent to the model — and
        // therefore which one the room reads in the "prompt as sent" panel.
        language: i18n.lang,
        overrides: overridesForRequest(),
        prompt_override: state.promptEdits.get(state.beatId) ?? null,
      }),
    });

    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      showBanner(
        detail.detail || t("harness.run_refused", { status: res.status }), "error");
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
      return showBanner(t("harness.chain_failed", { error: data.error }), "error");
    case "run_done": return onRunDone(data);
  }
}

function onPlan(plan) {
  $("#prompt").textContent = plan.prompt;      // the prompt as actually sent
  setPromptSummary(true);                      // and now the label is earned
  if (plan.teaches) $("#teaches").textContent = plan.teaches;
  // Live is announced as loudly as replay. If only replay were labelled, a
  // room would have to notice an absence to know what it is watching.
  const mode = $("#mode");
  mode.hidden = false;
  mode.dataset.mode = plan.replayed ? "replay" : "live";
  mode.textContent = plan.replayed ? t("harness.mode_replay") : t("harness.mode_live");

  const host = $("#panes");
  host.innerHTML = "";
  host.dataset.count = plan.panes.length;

  for (const pane of plan.panes) {
    const card = el("article", "pane");
    card.dataset.pane = pane.pane;
    card.dataset.role = pane.role || "";
    card.innerHTML =
      `<header>` +
        `<span class="pane-label">${escapeHtml(pane.label)}</span>` +
        `<button type="button" class="pane-zoom" data-zoom-pane ` +
          `title="${escapeHtml(t("harness.zoom_pane"))}">&#10530;</button>` +
        `<span class="pane-state" data-state="waiting">${escapeHtml(t("harness.pane_waiting"))}</span>` +
      `</header>` +
      `<div class="meta mono">${paneMeta(pane)}</div>` +
      documentChips(pane) +
      contextNode(pane) +
      `<div class="out"></div>`;
    host.append(card);
  }

  if (plan.degraded) showBanner(t("harness.degraded"), "warn");
}

// D3's rung, on the pane that stands on it. Objective 2 says the room can see
// "over which retrieved passages"; this is that sentence made literal.
//
// Rung 2 gets a measure and not the text. Projecting eleven thousand characters
// of house documents teaches nobody anything, whereas "every document — 11.240
// characters" next to a pane that says "no documents" is the whole rung in one
// line. Rung 3 gets the passages themselves, each with its file and score,
// because checking them against the answer is what the beat asks the room to do.
// The documents behind this pane, as things you can open. The room is asked to
// check the answer against them; a citation it cannot open is a citation it has
// to take on trust, which is the habit this lesson exists to break.
function documentChips(pane) {
  const docs = pane.documents || [];
  if (!docs.length) return "";
  return `<p class="documents">` + docs.map((d) =>
    `<button type="button" class="doc-chip" data-document="${escapeHtml(d)}">` +
    `<span class="doc-icon" aria-hidden="true">&#128196;</span>` +
    `<span class="mono">${escapeHtml(d.split("/").pop())}</span></button>`).join("") +
    `</p>`;
}

function contextNode(pane) {
  if (!pane.context || pane.context === "none") return "";

  const chars = new Intl.NumberFormat(i18n.lang).format(pane.context_chars || 0);

  if (pane.context === "all") {
    return `<p class="context mono" data-context="all">` +
      `${escapeHtml(t("harness.context_all", { chars }))}</p>`;
  }

  const passages = pane.passages || [];
  if (!passages.length) return "";

  const items = passages.map((p) =>
    `<li>` +
      `<button type="button" class="passage-source mono" data-document="${escapeHtml(p.source)}">` +
        `${escapeHtml(p.source)}</button>` +
      `<span class="passage-score mono">${escapeHtml(t("harness.passage_score", {
        score: Number(p.score).toFixed(2) }))}</span>` +
      `<p class="passage-text">${escapeHtml(p.text)}</p>` +
    `</li>`).join("");

  return `<details class="context passages" data-context="retrieved" open>` +
    `<summary>${escapeHtml(t("harness.context_retrieved", { count: passages.length }))}</summary>` +
    `<ol class="passage-list">${items}</ol>` +
    `</details>`;
}

// Provider, model, temperature, thinking budget and destination — the mechanism
// this whole application exists to put on a screen (PROJECT.md objective 2).
function paneMeta(pane) {
  if (pane.unavailable) {
    return `<span class="unavailable">${escapeHtml(t("harness.unavailable"))}</span>`;
  }
  const bits = [`${escapeHtml(pane.provider)} · ${escapeHtml(pane.model)}`];
  // Never state a temperature the call did not carry. Two things can stop it:
  // the model ignores sampling parameters, or the installed SDK has no field
  // for them — anthropic 1.2.0 dropped `temperature` from Messages.create
  // outright. Either way the number is not in flight, and a false number here
  // is worse than none.
  bits.push(pane.temperature_applies === false
    ? `<span class="unavailable">${escapeHtml(
        t("harness.temperature_ignored", { value: pane.temperature }))}</span>`
    : escapeHtml(t("harness.temperature", { value: pane.temperature })));
  if (pane.thinking) {
    bits.push(escapeHtml(t("harness.thinking", { level: pane.thinking })));
  }
  bits.push(
    `<span class="target ${pane.local ? "local" : "remote"}">` +
    `${pane.local ? escapeHtml(t("harness.local")) : "→"} ${escapeHtml(pane.egress)}</span>`
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
  setState(i, t("harness.pane_streaming"), "streaming");
  out.scrollTop = out.scrollHeight;
}

function onPaneDone({ pane: i, egress, local }) {
  setState(i, t("harness.pane_done"), "done");
  noteEgress(egress, local);
}

function onPaneFailed({ pane: i, error }) {
  setState(i, t("harness.pane_failed"), "failed");
  const out = pane(i)?.querySelector(".out");
  if (out) {
    const p = el("p", "failure");
    p.textContent = error;   // narrated, not hidden — and never translated
    out.append(p);
  }
}

function onPaneUnavailable({ pane: i, reason, recording }) {
  setState(i, t("harness.pane_unavailable"), "unavailable");
  const out = pane(i)?.querySelector(".out");
  if (!out) return;
  const p = el("p", "failure");
  p.textContent = recording
    ? t("harness.replaying", { reason })
    : t("harness.no_recording", { reason });
  out.append(p);
}

function onRunDone(done) {
  if (done.produced) showBanner(t("harness.chain_written", { file: done.produced }), "ok");
  else if (done.chain_held) showBanner(t("harness.chain_held"), "warn");
  // Kept the moment it finishes, not only when the trainer navigates away: a
  // reload or a language switch mid-lesson must not be what loses it.
  if (state.beatId) {
    rememberResult(state.beatId);
    $("#reset-run").hidden = false;
    document.querySelector(`#beats li[data-id="${state.beatId}"]`)
      ?.classList.add("has-result");
  }
}

function noteEgress(target, local) {
  if (!target) return;
  state.egress.set(target, local);

  const entries = [...state.egress];
  $("#egress-targets").innerHTML = entries
    .map(([target_, isLocal]) =>
      `<span class="target ${isLocal ? "local" : "remote"}">${escapeHtml(target_)}</span>`)
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

boot().catch((err) =>
  showBanner(t("harness.server_unreachable", { error: String(err) }), "error"));

// ── the viewer ─────────────────────────────────────────────────────────────
//
// One overlay for every "let me look at that properly" on this surface: a pane
// at full page, the prompt (editable, for the next run only), and any document
// a pane put in front of the question. Same controls in all three cases,
// because it is the same gesture and a room should not have to learn two ways
// to make text bigger.
//
// The font size is the point of it. A trainer reads a passage aloud from the
// back of a room; 14px does not survive that, and neither does a projector at
// the wrong resolution. It is remembered for the session so the size chosen
// once in the first demo still holds in the fifth.

const VIEWER_STEPS = [0.9, 1, 1.2, 1.45, 1.75, 2.1, 2.5, 3];
let viewerStep = 2;
let viewerOnSave = null;

function viewerScale() {
  $("#viewer").style.setProperty("--viewer-scale", VIEWER_STEPS[viewerStep]);
}

function openViewer({ title, text, note = "", editable = false, onSave = null }) {
  const box = $("#viewer");
  $("#viewer-title").textContent = title;
  $("#viewer-note").textContent = note;
  $("#viewer-body").textContent = text;
  const edit = $("#viewer-edit");
  edit.value = text;
  edit.hidden = !editable;
  $("#viewer-body").hidden = editable;
  viewerOnSave = editable ? onSave : null;
  box.hidden = false;
  viewerScale();
  (editable ? edit : $("#viewer-body")).focus();
}

function closeViewer() {
  // An edit is taken on the way out rather than behind a Save button: the
  // trainer's next gesture is pressing Esegui, and a change that silently did
  // not apply is worse than no editing at all.
  if (viewerOnSave) viewerOnSave($("#viewer-edit").value);
  viewerOnSave = null;
  $("#viewer").hidden = true;
}

$("#viewer-close").addEventListener("click", closeViewer);
$("#viewer-bigger").addEventListener("click", () => {
  viewerStep = Math.min(viewerStep + 1, VIEWER_STEPS.length - 1);
  viewerScale();
});
$("#viewer-smaller").addEventListener("click", () => {
  viewerStep = Math.max(viewerStep - 1, 0);
  viewerScale();
});
document.addEventListener("keydown", (e) => {
  if ($("#viewer").hidden) return;
  if (e.key === "Escape") closeViewer();
  if (e.key === "+" || e.key === "=") $("#viewer-bigger").click();
  if (e.key === "-") $("#viewer-smaller").click();
});

// ── the prompt, opened and edited ──────────────────────────────────────────
//
// An edit applies to the next run and is then discarded. It is never written
// back to demo-prompts.json: that file is vendored from the deck at the commit
// in DECK-PIN.txt (ADR 0001), so an edit that changed it would put Banco and
// the slides on two different texts without saying so.

$("#prompt-open").addEventListener("click", (e) => {
  e.preventDefault();
  const beat = beatById(state.beatId);
  if (!beat) return;
  openViewer({
    title: t("harness.prompt_summary"),
    text: $("#prompt").textContent,
    note: state.promptEdits.has(state.beatId) ? t("harness.prompt_edited") : "",
    editable: true,
    onSave: (value) => {
      const original = beat.run.prompt || "";
      if (value.trim() && value !== original) state.promptEdits.set(state.beatId, value);
      else state.promptEdits.delete(state.beatId);
      $("#prompt").textContent = state.promptEdits.get(state.beatId) ?? original;
      setPromptSummary(beat.run.prompt_complete);
    },
  });
});

// ── documents a pane put in front of the question ──────────────────────────

async function openDocument(path) {
  const url = withLang(`/api/document?sector=${encodeURIComponent(state.sector)}` +
    `&path=${encodeURIComponent(path)}`);
  openViewer({ title: path, text: t("harness.document_loading") });
  try {
    const doc = await json(url);
    openViewer({ title: path, text: doc.text });
  } catch (err) {
    // Narrated in the viewer that was already opened, not swallowed: a
    // document the room was invited to check and cannot open is a fact.
    openViewer({ title: path, text: t("harness.document_failed", { error: String(err) }) });
  }
}

// Delegated, because panes are rebuilt on every run and restored from a
// snapshot when the trainer comes back to a beat.
$("#panes").addEventListener("click", (e) => {
  const doc = e.target.closest("[data-document]");
  if (doc) { openDocument(doc.dataset.document); return; }
  const zoom = e.target.closest("[data-zoom-pane]");
  if (zoom) {
    const card = zoom.closest(".pane");
    openViewer({
      title: card.querySelector(".pane-label")?.textContent || "",
      text: card.querySelector(".out")?.textContent || "",
      note: card.querySelector(".meta")?.textContent || "",
    });
  }
});

// ── the gear: provider, model and reasoning per role ───────────────────────
//
// Roles, never panes. `run-blocks.json` asks for `primary` / `secondary` /
// `local` and never names a provider (ADR 0003); the gear rebinds the role, so
// a beat keeps degrading to replay when a source disappears instead of
// breaking. It also means one choice covers every pane that asked for that
// role, which is what a trainer means by "run this demo on the small model".

$("#gear").addEventListener("click", async () => {
  const panel = $("#gear-panel");
  const open = panel.hidden;
  $("#gear").setAttribute("aria-expanded", String(open));
  panel.hidden = !open;
  if (!open) return;
  if (!state.catalogue) {
    panel.innerHTML = `<p class="gear-loading">${escapeHtml(t("harness.gear_loading"))}</p>`;
    try {
      state.catalogue = (await json("/api/sources/catalogue")).sources || [];
    } catch {
      state.catalogue = [];
    }
  }
  renderGear();
});

function rolesOfCurrentBeat() {
  const block = beatById(state.beatId);
  if (!block) return [];
  // Roles are not in the beat payload, so they come from the panes the last
  // run laid out, falling back to the two that every beat can use.
  const seen = [...document.querySelectorAll("#panes .pane")]
    .map((p) => p.dataset.role).filter(Boolean);
  return [...new Set(seen.length ? seen : ["primary", "secondary", "local"])];
}

function renderGear() {
  const panel = $("#gear-panel");
  if (!state.catalogue.length) {
    panel.innerHTML = `<p class="gear-loading">${escapeHtml(t("harness.gear_none"))}</p>`;
    return;
  }
  panel.innerHTML = rolesOfCurrentBeat().map((role) => {
    const chosen = state.overrides[role] || {};
    const providers = state.catalogue.map((s) =>
      `<option value="${escapeHtml(s.provider)}"${s.provider === chosen.provider ? " selected" : ""}>` +
      `${escapeHtml(s.provider)}</option>`).join("");
    const source = state.catalogue.find((s) => s.provider === chosen.provider);
    const models = (source ? source.models : []).map((m) =>
      `<option value="${escapeHtml(m)}"${m === chosen.model ? " selected" : ""}>${escapeHtml(m)}</option>`
    ).join("");
    return `<div class="gear-role" data-role="${escapeHtml(role)}">` +
      `<span class="gear-role-name mono">${escapeHtml(role)}</span>` +
      `<select data-gear="provider"><option value="">${escapeHtml(t("harness.gear_default"))}</option>${providers}</select>` +
      `<select data-gear="model"><option value="">${escapeHtml(t("harness.gear_default"))}</option>${models}</select>` +
      `<select data-gear="think">` +
        `<option value="">${escapeHtml(t("harness.gear_default"))}</option>` +
        `<option value="false"${chosen.think === "false" ? " selected" : ""}>${escapeHtml(t("harness.gear_think_off"))}</option>` +
        `<option value="low"${chosen.think === "low" ? " selected" : ""}>low</option>` +
        `<option value="medium"${chosen.think === "medium" ? " selected" : ""}>medium</option>` +
        `<option value="high"${chosen.think === "high" ? " selected" : ""}>high</option>` +
      `</select></div>`;
  }).join("") + `<p class="gear-note">${escapeHtml(t("harness.gear_note"))}</p>`;
}

$("#gear-panel").addEventListener("change", (e) => {
  const field = e.target.dataset.gear;
  if (!field) return;
  const role = e.target.closest(".gear-role").dataset.role;
  const current = state.overrides[role] || {};
  const value = e.target.value;
  if (!value) delete current[field]; else current[field] = value;
  // Changing the provider invalidates whichever model was chosen under the old
  // one: offering gpt-5 under Anthropic would be a control that cannot work.
  if (field === "provider") delete current.model;
  if (Object.keys(current).length) state.overrides[role] = current;
  else delete state.overrides[role];
  renderGear();
});

// `think: "false"` arrives from a <select>, which only carries strings. The
// provider adapters distinguish a boolean from a level, so it is converted
// here rather than left for each of the four to guess at.
function overridesForRequest() {
  const out = {};
  for (const [role, choice] of Object.entries(state.overrides)) {
    const copy = { ...choice };
    if (copy.think === "false") copy.think = false;
    out[role] = copy;
  }
  return out;
}
