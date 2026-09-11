// Stage console. Never projected. Reads state from the server and writes keys to
// it; no stored key is ever rendered here, masked or otherwise.
const $ = (s) => document.querySelector(s);
const state = { sector: localStorage.getItem("banco.sector") || "numismatics" };

async function boot() {
  await refresh();
  // Ollama's reachability probe waits on a socket, so the page renders first and
  // fills this in after: a trainer opening the console should not watch a blank
  // screen while a port times out.
  refreshOllama();
}

async function refresh() {
  const res = await fetch(`/console/preflight?sector=${encodeURIComponent(state.sector)}&probe=false`);
  if (res.status === 401) return;               // the browser will prompt
  const data = await res.json();

  $("#profile").textContent = data.profile;
  $("#profile").dataset.profile = data.profile;
  $("#unprotected").hidden = !data.unprotected;
  $("#to-harness").hidden = !data.ready_to_run;

  for (const [provider, present] of Object.entries(data.api_keys)) {
    const node = $(`#state-${provider}`);
    if (!node) continue;
    node.textContent = present ? "key stored" : "not set";
    node.dataset.set = String(present);
  }

  const pw = data.checks.admin_password;
  $("#state-admin").textContent = pw.ok ? "set" : "not set";
  $("#state-admin").dataset.set = String(pw.ok);

  renderChecks(data.checks);
}

function renderChecks(checks) {
  const order = ["admin_password", "chain", "recordings"];
  $("#checks").innerHTML = order.map((key) => {
    const c = checks[key];
    return `<li data-ok="${c.ok}">` +
      `<span class="mark">${c.ok ? "OK" : "··"}</span>` +
      `<span>${escapeHtml(c.detail)}` +
      (c.action ? ` <span class="action">${escapeHtml(c.action)}</span>` : "") +
      `</span></li>`;
  }).join("");
}

async function refreshOllama() {
  const res = await fetch("/console/ollama");
  if (!res.ok) return;
  const o = await res.json();

  $("#state-ollama").textContent = o.running ? "running" : o.installed ? "installed, not running" : "not installed";
  $("#state-ollama").dataset.set = String(o.running);
  $("#ollama-url").placeholder = o.base_url || "http://localhost:11434";

  const ram = o.system?.ram_gb ? `${o.system.ram_gb.toFixed(1)} GB RAM` : null;
  const gpu = o.system?.gpu_name || null;
  $("#ollama-summary").textContent = o.error
    ? o.error
    : o.running
      ? [`Reachable at ${o.base_url}`, ram, gpu].filter(Boolean).join(" · ")
      : o.installed
        ? "Installed but not answering. Start Ollama, then reload."
        : "Not installed. Banco runs without it; the offline profile does not.";

  $("#ollama-models").innerHTML = o.models?.length
    ? o.models.map((m) => `<li><span class="mark">OK</span><span>${escapeHtml(m)}</span></li>`).join("")
    : `<li class="note">none</li>`;

  $("#ollama-recommended").innerHTML = o.recommended?.length
    ? o.recommended.map((m) => {
        const installed = (o.models || []).includes(m.name);
        return `<li data-ok="${installed}">` +
          `<span class="mark">${installed ? "OK" : "··"}</span>` +
          `<span>${escapeHtml(m.name)} <span class="action">${escapeHtml(m.description || "")}</span></span>` +
          (installed ? "" : `<button class="pull" data-model="${escapeHtml(m.name)}">pull</button>`) +
          `</li>`;
      }).join("")
    : `<li class="note">—</li>`;

  document.querySelectorAll(".pull").forEach((b) =>
    b.addEventListener("click", () => pull(b.dataset.model, b)));
}

// Ollama reports pull progress as a stream of JSON lines; they are relayed
// verbatim so what is shown is what the server said, not a summary of it.
async function pull(model, button) {
  button.disabled = true;
  const log = $("#pull-log");
  log.hidden = false;
  log.textContent = `pulling ${model}\n`;

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

  const res = await fetch("/console/keys", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  $("#saved").textContent = res.ok ? data.detail : (data.detail || "could not save");

  // Clear the inputs immediately: a key sitting in a form field is a key on a
  // screen, and this machine goes to client sites.
  event.target.querySelectorAll('input[type="password"]').forEach((i) => (i.value = ""));
  await refresh();
  refreshOllama();
});

// The live check spends a call per source, so it never runs on load — it runs
// when a trainer asks, which is once, before the lesson.
$("#run-check").addEventListener("click", async () => {
  const button = $("#run-check");
  button.disabled = true;
  $("#check-note").textContent = "calling each source…";

  try {
    const res = await fetch(`/console/check?sector=${encodeURIComponent(state.sector)}`,
                            { method: "POST" });
    const data = await res.json();
    renderChecks(data.checks);
    renderLive(data.live);
    $("#check-note").textContent = data.all_sources_live
      ? "every configured source answered"
      : "at least one source did not answer — see below";
    $("#to-harness").hidden = !data.ready_to_run;
  } catch (err) {
    $("#check-note").textContent = String(err);
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
    : `<li class="note">no source configured to call</li>`;
}

$("#reset-transcripts").addEventListener("click", async () => {
  await fetch("/console/transcripts/reset", { method: "POST" });
  $("#reset-transcripts").textContent = "Forgotten";
  setTimeout(() => ($("#reset-transcripts").textContent = "Forget rehearsal transcripts"), 1500);
});

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

boot();
