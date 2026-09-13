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
  for (const beat of state.demo.prompts || []) {
    const li = el("li", beat.run.runnable ? "runnable" : "blocked-beat");
    li.dataset.id = beat.id;
    li.innerHTML =
      `<span class="beat-id">${escapeHtml(beat.id)}</span>` +
      `<span class="beat-label">${escapeHtml(pick(beat, "label"))}</span>` +
      `<span class="beat-panes">${escapeHtml(beat.run.runnable
        ? t("harness.beat_panes", { count: beat.run.panes })
        : t("harness.beat_no_panes"))}</span>`;
    li.addEventListener("click", () => selectBeat(beat.id));
    list.append(li);
  }

  const wanted = state.beatId && beatById(state.beatId)
    ? state.beatId
    : (state.demo.prompts || []).find((p) => p.run.runnable)?.id;

  if (wanted) selectBeat(wanted, { keepPanes });
  else { $("#detail").hidden = true; if (!keepPanes) $("#panes").innerHTML = ""; }
}

function beatById(id) {
  return (state.demo.prompts || []).find((p) => p.id === id);
}

function selectBeat(id, { keepPanes = false } = {}) {
  const beat = beatById(id);
  if (!beat) return;
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
  $("#panes").innerHTML = "";
  $("#banner").hidden = true;
}

// The panel's label is a claim about the text under it, so it follows the text.
// `data-i18n` is rewritten rather than bypassed: the language switch rebuilds
// every marked node from the catalogue, and a label set only here would be
// replaced by whichever key the markup still carried.
function setPromptSummary(complete) {
  const key = complete ? "harness.prompt_summary" : "harness.prompt_summary_template";
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
    card.innerHTML =
      `<header>` +
        `<span class="pane-label">${escapeHtml(pane.label)}</span>` +
        `<span class="pane-state" data-state="waiting">${escapeHtml(t("harness.pane_waiting"))}</span>` +
      `</header>` +
      `<div class="meta mono">${paneMeta(pane)}</div>` +
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
      `<span class="passage-source mono">${escapeHtml(p.source)}</span>` +
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
