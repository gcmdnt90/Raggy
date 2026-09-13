// Banco i18n, client side. Loaded by both surfaces, before their own script.
//
// The language is a property of the browser that is looking, not of the server:
// the console and the harness are open at once, often on two screens, and the
// trainer's console must be able to be in Italian while a visiting room reads
// English — or the reverse. So it lives in localStorage and travels to the
// server as a `lang` parameter per request. There is no server-side session.
//
// Static text is marked up in the HTML:
//
//     <span data-i18n="harness.run">Esegui</span>
//     <input data-i18n-placeholder="console.password_placeholder">
//     <nav data-i18n-aria-label="harness.demos_aria">
//
// The text written in the HTML is the Italian one, so a page renders correctly
// in the default language before this file has run. Any `data-i18n-*` attribute
// sets the attribute named by its suffix.
//
// Strings that JavaScript builds are fetched with `i18n.t(key, vars)`.
// Strings the server generates are translated server-side (app/i18n.py) and
// arrive already written; strings a *model* produced are never translated.

(function (global) {
  const STORAGE_KEY = "banco.lang";
  const DEFAULT = "it";
  const FALLBACK = "en";
  const SUPPORTED = ["it", "en"];
  const EVENT = "banco:language";

  const catalogs = global.BancoStrings || {};

  function stored() {
    // localStorage throws in a browser with site data blocked, and Banco is
    // carried to client machines: a locked-down browser must still render the
    // page in the default language rather than fail at the first line.
    try {
      const value = localStorage.getItem(STORAGE_KEY);
      if (SUPPORTED.includes(value)) return value;
    } catch {}
    return DEFAULT;
  }

  let current = stored();

  function t(key, vars) {
    const entry =
      (catalogs[current] && catalogs[current][key]) ??
      (catalogs[DEFAULT] && catalogs[DEFAULT][key]) ??
      (catalogs[FALLBACK] && catalogs[FALLBACK][key]);
    // A missing key shows as the key: visible, reportable, and never a blank
    // line pretending to be a working label.
    if (entry === undefined) return key;
    if (!vars) return entry;
    return entry.replace(/\{(\w+)\}/g, (whole, name) =>
      Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : whole);
  }

  // Only ever writes textContent and attribute values — never innerHTML, so a
  // catalogue entry cannot introduce markup into either surface.
  function apply(root) {
    const scope = root || document;

    scope.querySelectorAll("[data-i18n]").forEach((node) => {
      node.textContent = t(node.getAttribute("data-i18n"));
    });

    scope.querySelectorAll("*").forEach((node) => {
      for (const attribute of node.attributes) {
        if (!attribute.name.startsWith("data-i18n-")) continue;
        const target = attribute.name.slice("data-i18n-".length);
        if (!target) continue;
        node.setAttribute(target, t(attribute.value));
      }
    });

    document.documentElement.lang = current;
  }

  function set(lang) {
    const next = SUPPORTED.includes(lang) ? lang : DEFAULT;
    if (next === current) return;
    current = next;
    try { localStorage.setItem(STORAGE_KEY, current); } catch {}
    apply();
    syncSelectors();
    dispatchEvent(new CustomEvent(EVENT, { detail: { lang: current } }));
  }

  function syncSelectors() {
    document.querySelectorAll("[data-lang-select]").forEach((select) => {
      select.value = current;
    });
  }

  // Every surface gets the switch for free by putting `data-lang-select` on a
  // <select>; no page has to wire it up, and none can forget to.
  function bind() {
    document.querySelectorAll("[data-lang-select]").forEach((select) => {
      if (select.dataset.langBound) return;
      select.dataset.langBound = "1";
      select.addEventListener("change", () => set(select.value));
    });
    syncSelectors();
  }

  global.i18n = {
    t,
    apply,
    set,
    bind,
    get lang() { return current; },
    SUPPORTED,
    DEFAULT,
    EVENT,
  };

  apply();
  bind();
})(window);
