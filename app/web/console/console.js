// Stage console. Never projected. Reads state from the server and writes keys to
// it; no stored key is ever rendered here, masked or otherwise.
//
// Two kinds of text appear on this page. Banco's own words come from `i18n.t`,
// or arrive already translated because app/i18n.py composed them — which is why
// every request below carries `lang`. A provider's own error message is never
// translated: it is evidence, and a rewritten error is no longer what the
// provider said.
const $ = (s) => document.querySelector(s);
const t = (key, vars) => i18n.t(key, vars);

const state = { sector: localStorage.getItem("banco.sector") || "numismatics" };

async function boot() {
  // The first read skips Ollama's reachability probe, which waits up to three
  // seconds on a socket: a trainer opening the console should not watch a blank
  // screen while a port times out.
  try {
    await refresh();
  } catch (err) {
    fail(err);
  }

  // Outside the try above, because a console that cannot draw pre-flight must
  // still be able to say whether Ollama is running.
  await refreshOllama();

  // And then pre-flight again, *with* the probe. The unprobed read assumes the
  // local source is there — so on a machine with no Ollama at all it reported
  // the `offline` profile and offered the harness link, while the card directly
  // below said "not installed". A profile is shown as derived from what this
  // machine can actually reach; until something has reached, it has not been
  // measured, and a figure shown as a measurement was measured.
  refresh(true).catch(fail);
}

// A console that fails silently is worse than one that fails: a blank panel
// reads as "nothing to report" minutes before a lesson.
function fail(err) {
  console.error(err);
  $("#check-note").textContent = t("console.preflight_failed", { error: String(err) });
}

// The language is the browser's, never the server's (AGENTS.md rule 9), so it
// travels on every request that can come back with server-composed text.
function withLang(url) {
  return `${url}${url.includes("?") ? "&" : "?"}lang=${encodeURIComponent(i18n.lang)}`;
}

// `probe` decides whether the local source is *asked* or assumed. Only the
// first paint may assume, and it corrects itself moments later (see `boot`).
async function refresh(probe = false, retry = true) {
  const res = await fetch(withLang(
    `/console/preflight?sector=${encodeURIComponent(state.sector)}&probe=${probe}`));
  if (res.status === 401) return;               // the browser will prompt
  const data = await res.json();

  // The remembered sector can be absent from the database — a pack renamed, or
  // a machine that ran a different deck. The report just read is about a sector
  // that does not exist, so it is replaced and read again rather than rendered.
  const sectors = data.sectors || [];
  if (retry && sectors.length && !sectors.some((s) => s.id === state.sector)) {
    setSector(sectors[0].id);
    return refresh(probe, false);
  }

  renderSectors(sectors);
  renderMaterial(data.demo_data, data.checks.demo_data);
  renderDeck(data.deck);

  $("#profile").textContent = data.profile;
  $("#profile").dataset.profile = data.profile;
  $("#unprotected").hidden = !data.unprotected;
  $("#to-harness").hidden = !data.ready_to_run;

  for (const [provider, present] of Object.entries(data.api_keys)) {
    const node = $(`#state-${provider}`);
    if (!node) continue;
    node.textContent = present ? t("console.key_stored") : t("console.not_set");
    node.dataset.set = String(present);
  }

  const pw = data.checks.admin_password;
  $("#state-admin").textContent = pw.ok ? t("console.is_set") : t("console.not_set");
  $("#state-admin").dataset.set = String(pw.ok);

  renderChecks(data.checks);
}

function setSector(id) {
  state.sector = id;
  localStorage.setItem("banco.sector", id);
}

// The picker is built from what the server says the database declares. A sector
// whose pack was never generated stays in the list and is marked: the trainer
// who needs to know it is missing is the one about to select it, and a sector
// that silently disappears reads as a database that lost it.
function renderSectors(sectors) {
  const select = $("#sector");
  const status = $("#state-sector");

  if (!sectors.length) {
    select.innerHTML = `<option value="">${escapeHtml(t("console.no_sector"))}</option>`;
    status.textContent = t("console.none");
    status.dataset.set = "false";
    return;
  }

  select.innerHTML = sectors.map((s) =>
    `<option value="${escapeHtml(s.id)}"${s.id === state.sector ? " selected" : ""}>` +
    `${escapeHtml(s.label || s.id)}${s.ready ? "" : escapeHtml(t("console.sector_missing"))}</option>`
  ).join("");

  const chosen = sectors.find((s) => s.id === state.sector);
  const ready = Boolean(chosen && chosen.ready);
  status.textContent = ready ? t("console.sector_ready") : t("console.sector_incomplete");
  status.dataset.set = String(ready);

  // Assigned rather than added: this select is rebuilt on every refresh, and
  // addEventListener would stack one more handler each time.
  select.onchange = () => {
    setSector(select.value);
    refresh(true).catch(fail);
  };
}

// Per demo, because a sector pack is complete or it cannot run, and the beats
// Banco cannot execute yet are still performed in the room from this folder.
function renderMaterial(material, check) {
  const list = $("#material");
  const action = $("#material-action");
  action.hidden = !(check && !check.ok && check.action);
  action.textContent = (check && check.action) || "";

  if (!material || material.unknown_sector) {
    list.innerHTML =
      `<li class="note">${escapeHtml((check && check.detail) || t("console.unknown_sector"))}</li>`;
    return;
  }

  const demos = Object.entries(material.demos || {});
  list.innerHTML = demos.length
    ? demos.map(([id, d]) => {
        // The trainer-only files are named here and nowhere else: this is the
        // one surface allowed to mention `_perito/ground-truth.csv`.
        const names = (d.missing || [])
          .map((m) => m.path + (m.trainer ? t("console.material_trainer") : ""))
          .join(", ");
        const detail = d.ok
          ? t("console.material_ok", { count: d.required })
          : t("console.material_missing", {
              count: (d.missing || []).length, total: d.required, names,
            });
        return `<li data-ok="${d.ok}">` +
          `<span class="mark">${d.ok ? "OK" : "··"}</span>` +
          `<span>${escapeHtml(String(id).toUpperCase())} — ${escapeHtml(detail)}</span></li>`;
      }).join("")
    : `<li class="note">${escapeHtml(t("console.dash"))}</li>`;
}

// The prompt text is shared with the theory-deck, so which build it came from is
// part of pre-flight: slides that disagree with what Banco sends are two
// different commits, and nothing else on this page would say so.
function renderDeck(deck) {
  $("#deck").textContent = deck
    ? t("console.deck", {
        version: deck.version,
        updated: deck.updated,
        pin: deck.pin || t("console.dash"),
        demos: deck.demos,
        sectors: deck.sectors,
      })
    : "";
}

function renderChecks(checks) {
  const order = ["demo_data", "admin_password", "chain", "recordings"];
  // Filtered, not assumed. A key the server stops sending used to throw here
  // and take the whole panel down with it — including the lines that were fine,
  // and including the "run the full check" result, which is where a trainer
  // looks last before a lesson.
  $("#checks").innerHTML = order.filter((key) => checks && checks[key]).map((key) => {
    const c = checks[key];
    return `<li data-ok="${c.ok}">` +
      `<span class="mark">${c.ok ? "OK" : "··"}</span>` +
      `<span>${escapeHtml(c.detail)}` +
      (c.action ? ` <span class="action">${escapeHtml(c.action)}</span>` : "") +
      `</span></li>`;
  }).join("");
}

async function refreshOllama() {
  const res = await fetch(withLang("/console/ollama"));
  if (!res.ok) return;
  const o = await res.json();

  $("#state-ollama").textContent = o.running
    ? t("console.ollama_running")
    : o.installed ? t("console.ollama_installed_not_running") : t("console.ollama_not_installed");
  $("#state-ollama").dataset.set = String(o.running);
  $("#ollama-url").placeholder = o.base_url || "http://localhost:11434";

  // RAM and GPU are device facts, not prose: the numbers and the adapter's own
  // name are shown as they are.
  const ram = o.system?.ram_gb ? t("console.ollama_ram", { gb: o.system.ram_gb.toFixed(1) }) : null;
  const gpu = o.system?.gpu_name || null;
  $("#ollama-summary").textContent = o.error
    ? o.error
    : o.running
      ? [t("console.ollama_reachable", { url: o.base_url }), ram, gpu].filter(Boolean).join(" · ")
      : o.installed
        ? t("console.ollama_installed_hint")
        : t("console.ollama_absent_hint");

  $("#ollama-models").innerHTML = o.models?.length
    ? o.models.map((m) => `<li><span class="mark">OK</span><span>${escapeHtml(m)}</span></li>`).join("")
    : `<li class="note">${escapeHtml(t("console.none"))}</li>`;

  $("#ollama-recommended").innerHTML = o.recommended?.length
    ? o.recommended.map((m) => {
        const installed = (o.models || []).includes(m.name);
        return `<li data-ok="${installed}">` +
          `<span class="mark">${installed ? "OK" : "··"}</span>` +
          `<span>${escapeHtml(m.name)} <span class="action">${escapeHtml(m.description || "")}</span></span>` +
          (installed ? "" : `<button class="pull" data-model="${escapeHtml(m.name)}">${escapeHtml(t("console.pull"))}</button>`) +
          `</li>`;
      }).join("")
    : `<li class="note">${escapeHtml(t("console.dash"))}</li>`;

  document.querySelectorAll(".pull").forEach((b) =>
    b.addEventListener("click", () => pull(b.dataset.model, b)));
}

// Ollama reports pull progress as a stream of JSON lines; they are relayed
// verbatim so what is shown is what the server said, not a summary of it.
async function pull(model, button) {
  button.disabled = true;
  const log = $("#pull-log");
  log.hidden = false;
  log.textContent = t("console.pulling", { model }) + "\n";

  const res = await fetch("/console/ollama/pull", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      const line = block.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        const payload = JSON.parse(line.slice(6));
        const pct = payload.total ? ` ${Math.round((payload.completed || 0) / payload.total * 100)}%` : "";
        log.textContent += `${payload.status || payload.error || ""}${pct}\n`;
      } catch { log.textContent += line.slice(6) + "\n"; }
      log.scrollTop = log.scrollHeight;
    }
  }
  button.disabled = false;
  refreshOllama();
}

$("#keys").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = Object.fromEntries([...form.entries()].filter(([, v]) => String(v).trim()));
  body.ollama_base_url = $("#ollama-url").value.trim();

  const res = await fetch(withLang("/console/keys"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  $("#saved").textContent = res.ok ? data.detail : (data.detail || t("console.could_not_save"));

  // Clear the inputs immediately: a key sitting in a form field is a key on a
  // screen, and this machine goes to client sites.
  event.target.querySelectorAll('input[type="password"]').forEach((i) => (i.value = ""));
  await refresh(true).catch(fail);
  refreshOllama();
});

// The live check spends a call per source, so it never runs on load — it runs
// when a trainer asks, which is once, before the lesson.
$("#run-check").addEventListener("click", async () => {
  const button = $("#run-check");
  button.disabled = true;
  $("#check-note").textContent = t("console.calling_sources");

  try {
    const res = await fetch(
      withLang(`/console/check?sector=${encodeURIComponent(state.sector)}`),
      { method: "POST" });
    const data = await res.json();
    renderChecks(data.checks);
    renderLive(data.live);
    $("#check-note").textContent = data.all_sources_live
      ? t("console.all_sources_live")
      : t("console.some_sources_dead");
    $("#to-harness").hidden = !data.ready_to_run;
  } catch (err) {
    fail(err);
  } finally {
    button.disabled = false;
  }
});

function renderLive(live) {
  const entries = Object.entries(live || {});
  $("#live").innerHTML = entries.length
    ? entries.map(([role, c]) =>
        `<li data-ok="${c.ok}">` +
        `<span class="mark">${c.ok ? "OK" : "!!"}</span>` +
        `<span>${escapeHtml(c.detail)}` +
        (c.action ? ` <span class="action">${escapeHtml(c.action)}</span>` : "") +
        `</span></li>`).join("")
    : `<li class="note">${escapeHtml(t("console.no_source_to_call"))}</li>`;
}

$("#reset-transcripts").addEventListener("click", async () => {
  const button = $("#reset-transcripts");
  await fetch("/console/transcripts/reset", { method: "POST" });
  button.textContent = t("console.forgotten");
  setTimeout(() => (button.textContent = t("console.forget_transcripts")), 1500);
});

// Changing the language re-asks the server rather than re-labelling what is on
// screen: every pre-flight line was composed by app/i18n.py in the language the
// request carried, so the words here are only as current as the last request.
addEventListener(i18n.EVENT, () => {
  refresh(true).catch(fail);
  refreshOllama();
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

boot();
