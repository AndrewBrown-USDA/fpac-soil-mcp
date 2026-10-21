/* FPAC Soil MCP Harness - browser client (vanilla JS, no build step). */
"use strict";

(() => {
  // -------------------------------------------------------------------------
  // Utilities
  // -------------------------------------------------------------------------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const state = {
    config: null,
    status: null,
    tools: [],
    resources: [],
    templates: [],
    prompts: [],
    presets: {},
    evals: [],
    evalResults: {},
    selectedEval: null,
    currentTool: null,
    currentPrompt: null,
    stopEvals: false,
  };

  async function api(path, { method = "GET", body } = {}) {
    const res = await fetch(path, {
      method,
      headers: body !== undefined ? { "Content-Type": "application/json" } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }
    if (!res.ok) {
      const err = new Error(data?.error?.message || `HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  let toastTimer = null;
  function toast(message, isError = false) {
    const t = $("#toast");
    t.textContent = message;
    t.classList.toggle("err", isError);
    t.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.add("hidden"), isError ? 7000 : 3500);
  }

  function el(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else if (k === "dataset") Object.assign(node.dataset, v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  function highlightJson(value) {
    const json = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    return escapeHtml(json ?? "null").replace(
      /(&quot;(?:\\u[a-fA-F0-9]{4}|\\[^u]|[^\\&]|&(?!quot;))*?&quot;)(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g,
      (m, str, colon, bool) => {
        if (str) return colon ? `<span class="k">${str}</span>${colon}` : `<span class="s">${str}</span>`;
        if (bool) return `<span class="b">${m}</span>`;
        if (m === "null") return `<span class="z">null</span>`;
        return `<span class="n">${m}</span>`;
      },
    );
  }

  const jsonBlock = (value) => el("pre", { class: "json", html: highlightJson(value) });
  const fmtMs = (ms) => (ms === undefined || ms === null ? "" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`);
  const isScalar = (v) => v === null || ["string", "number", "boolean"].includes(typeof v);

  function fmtScalar(v) {
    if (v === null) return "null";
    if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "");
    return String(v);
  }

  function copyText(text) {
    navigator.clipboard?.writeText(text).then(
      () => toast("Copied to clipboard"),
      () => toast("Copy failed", true),
    );
  }

  function downloadJson(name, value) {
    const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
    const a = el("a", { href: URL.createObjectURL(blob), download: `${name}.json` });
    document.body.append(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 0);
  }

  // -------------------------------------------------------------------------
  // Tabs
  // -------------------------------------------------------------------------
  function showTab(name) {
    $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.id === `panel-${name}`));
    if (name === "history") refreshHistory();
    if (name === "server") refreshServer();
  }

  // -------------------------------------------------------------------------
  // Connection
  // -------------------------------------------------------------------------
  function updateModeVisibility() {
    const mode = $("#connMode").value;
    $$(".stdio-only").forEach((n) => n.classList.toggle("hidden", mode !== "stdio"));
    $$(".url-only").forEach((n) => n.classList.toggle("hidden", mode === "stdio"));
    const url = $("#connUrl");
    if (mode === "sse" && (!url.value || url.value.endsWith("/mcp"))) url.value = "http://127.0.0.1:8000/sse";
    if (mode === "http" && (!url.value || url.value.endsWith("/sse"))) url.value = "http://127.0.0.1:8000/mcp";
  }

  async function loadConfig() {
    const cfg = await api("/api/config");
    state.config = cfg;
    $("#connMode").value = cfg.mcp.mode;
    $("#connCommand").value = cfg.mcp.command;
    $("#connArgs").value = cfg.mcp.args.join(" ");
    $("#connCwd").value = cfg.mcp.cwd;
    $("#connUrl").value = cfg.mcp.url;
    $("#toolTimeout").value = Math.round(cfg.mcp.toolTimeoutMs / 1000);
    for (const id of ["#connCommand", "#connArgs", "#connCwd"]) {
      $(id).disabled = !cfg.allowCommandOverride;
      if (!cfg.allowCommandOverride) $(id).title = "Overrides disabled (HARNESS_ALLOW_COMMAND_OVERRIDE=false)";
    }
    updateModeVisibility();
  }

  function renderConnection() {
    const s = state.status || {};
    const pill = $("#connPill");
    pill.className = `pill ${s.connected ? "pill-on" : "pill-off"}`;
    pill.textContent = s.connected ? `Connected (${s.connection?.mode})` : "Disconnected";
    const sv = s.serverVersion;
    $("#serverName").textContent = sv ? `${sv.name} ${sv.version || ""}` : "";
    $("#btnDisconnect").disabled = !s.connected;
  }

  async function refreshStatus() {
    try {
      const prev = state.status?.connected;
      state.status = await api("/api/status");
      renderConnection();
      if (state.status.connected && !prev) await loadCatalog();
      if (!state.status.connected && prev) toast("MCP connection closed", true);
    } catch {
      /* harness offline */
    }
  }

  async function connect(evt) {
    evt?.preventDefault();
    const mode = $("#connMode").value;
    const body = { mode };
    if (mode === "stdio") {
      if (state.config?.allowCommandOverride) {
        body.command = $("#connCommand").value.trim();
        body.args = $("#connArgs").value.trim();
        body.cwd = $("#connCwd").value.trim();
      }
    } else {
      body.url = $("#connUrl").value.trim();
      const token = $("#connToken").value.trim();
      if (token) body.authToken = token;
    }
    const pill = $("#connPill");
    pill.className = "pill pill-busy";
    pill.textContent = "Connecting...";
    $("#btnConnect").disabled = true;
    $("#connMessage").textContent = "";
    try {
      state.status = await api("/api/connect", { method: "POST", body });
      toast("Connected to MCP server");
      await loadCatalog();
    } catch (err) {
      state.status = err.data?.status || { connected: false };
      const tail = (state.status.stderrTail || []).slice(-5).map((l) => l.line).join(" | ");
      $("#connMessage").textContent = `Connection failed: ${err.message}${tail ? ` -- stderr: ${tail}` : ""}`;
      toast(`Connection failed: ${err.message}`, true);
    } finally {
      $("#btnConnect").disabled = false;
      renderConnection();
    }
  }

  async function disconnect() {
    state.status = await api("/api/disconnect", { method: "POST" });
    renderConnection();
    toast("Disconnected");
  }

  async function loadCatalog() {
    const [tools, resources, prompts] = await Promise.allSettled([
      api("/api/tools"),
      api("/api/resources"),
      api("/api/prompts"),
    ]);
    state.tools = tools.status === "fulfilled" ? tools.value.tools : [];
    state.resources = resources.status === "fulfilled" ? resources.value.resources : [];
    state.templates = resources.status === "fulfilled" ? resources.value.templates : [];
    state.prompts = prompts.status === "fulfilled" ? prompts.value.prompts : [];
    $("#countTools").textContent = state.tools.length;
    $("#countResources").textContent = state.resources.length + state.templates.length;
    $("#countPrompts").textContent = state.prompts.length;
    renderToolList();
    renderResourceList();
    renderPromptList();
  }

  // -------------------------------------------------------------------------
  // JSON-schema driven argument forms
  // -------------------------------------------------------------------------
  function deref(schema, root) {
    if (schema && schema.$ref && root) {
      const key = schema.$ref.replace(/^#\/(\$defs|definitions)\//, "");
      return (root.$defs || root.definitions || {})[key] || schema;
    }
    return schema || {};
  }

  function describeField(rawSchema, root) {
    const schema = deref(rawSchema, root);
    const variants = (schema.anyOf || schema.oneOf || [schema]).map((v) => deref(v, root));
    const types = [];
    let enumValues = schema.enum || null;
    let items = schema.items ? deref(schema.items, root) : null;
    for (const v of variants) {
      if (v.type) types.push(...[].concat(v.type));
      else if (v.properties) types.push("object");
      if (v.enum && !enumValues) enumValues = v.enum;
      if (v.items && !items) items = deref(v.items, root);
    }
    const nonNull = types.filter((t) => t !== "null");
    const allowsString = nonNull.includes("string");
    let kind = "json";
    if (nonNull.length === 1) {
      const t = nonNull[0];
      if (t === "boolean") kind = "boolean";
      else if (t === "number" || t === "integer") kind = t;
      else if (t === "string") kind = enumValues ? "enum" : "string";
      else if (t === "array") kind = items && items.type === "string" ? "string-list" : "json";
    } else if (!nonNull.includes("object") && !nonNull.includes("array") && nonNull.length > 0) {
      kind = nonNull.includes("number") || nonNull.includes("integer") ? "number" : "string";
    }
    const typeLabel = nonNull.length ? nonNull.join(" | ") + (types.includes("null") ? " | null" : "") : "any";
    return { kind, typeLabel, enumValues, allowsString, schema };
  }

  function valueToInput(kind, value) {
    if (value === undefined || value === null) return "";
    if (kind === "json") return typeof value === "string" ? value : JSON.stringify(value, null, 2);
    if (kind === "string-list") return Array.isArray(value) ? value.join("\n") : String(value);
    if (kind === "boolean") return value ? "true" : "false";
    return String(value);
  }

  function buildArgForm(form, inputSchema, values = {}) {
    form.innerHTML = "";
    const props = inputSchema?.properties || {};
    const required = new Set(inputSchema?.required || []);
    const names = Object.keys(props);
    if (names.length === 0) {
      form.append(el("p", { class: "muted", text: "This tool takes no arguments." }));
      return;
    }
    for (const name of names) {
      const info = describeField(props[name], inputSchema);
      const def = info.schema.default;
      const initial = values[name] !== undefined ? values[name] : undefined;
      const id = `arg-${name}`;
      let input;
      if (info.kind === "boolean") {
        input = el(
          "select",
          { id },
          el("option", { value: "", text: def !== undefined ? `(default: ${def})` : "(unset)" }),
          el("option", { value: "true", text: "true" }),
          el("option", { value: "false", text: "false" }),
        );
      } else if (info.kind === "enum") {
        input = el(
          "select",
          { id },
          el("option", { value: "", text: def !== undefined ? `(default: ${def})` : "(unset)" }),
          info.enumValues.map((v) => el("option", { value: v, text: v })),
        );
      } else if (info.kind === "json" || info.kind === "string-list") {
        input = el("textarea", {
          id,
          spellcheck: "false",
          placeholder:
            info.kind === "string-list"
              ? "One value per line (or comma-separated)"
              : def !== undefined && def !== null
                ? JSON.stringify(def)
                : info.allowsString
                  ? "GeoJSON object, or a raw string such as WKT"
                  : "JSON value",
        });
      } else {
        input = el("input", {
          id,
          type: info.kind === "number" || info.kind === "integer" ? "number" : "text",
          step: info.kind === "integer" ? "1" : "any",
          placeholder: def !== undefined && def !== null ? String(def) : "",
        });
      }
      input.value = valueToInput(info.kind, initial);
      input.dataset.name = name;
      input.dataset.kind = info.kind;
      input.dataset.allowsString = info.allowsString ? "1" : "";
      input.dataset.required = required.has(name) ? "1" : "";

      const field = el(
        "div",
        { class: `field ${info.kind === "json" ? "full" : ""}` },
        el(
          "label",
          { for: id, class: "label-row" },
          name,
          el("span", { class: "type", text: info.typeLabel }),
          required.has(name) ? el("span", { class: "req", text: "required" }) : null,
        ),
        input,
        info.schema.description || info.schema.title
          ? el("span", { class: "help", text: info.schema.description || info.schema.title })
          : null,
      );
      form.append(field);
    }
  }

  function collectArgs(form) {
    const args = {};
    const errors = [];
    for (const input of $$("[data-name]", form)) {
      const { name, kind, allowsString, required } = input.dataset;
      const field = input.closest(".field");
      field?.classList.remove("invalid");
      const raw = input.value.trim();
      if (raw === "") {
        if (required) {
          errors.push(`${name} is required`);
          field?.classList.add("invalid");
        }
        continue;
      }
      try {
        if (kind === "number" || kind === "integer") {
          const n = Number(raw);
          if (!Number.isFinite(n)) throw new Error("not a number");
          args[name] = n;
        } else if (kind === "boolean") {
          args[name] = raw === "true";
        } else if (kind === "string-list") {
          args[name] = raw.startsWith("[") ? JSON.parse(raw) : raw.split(/[\n,]/).map((s) => s.trim()).filter(Boolean);
        } else if (kind === "json") {
          try {
            args[name] = JSON.parse(raw);
          } catch (e) {
            if (allowsString) args[name] = raw;
            else throw e;
          }
        } else {
          args[name] = raw;
        }
      } catch (e) {
        errors.push(`${name}: ${e.message}`);
        field?.classList.add("invalid");
      }
    }
    return { args, errors };
  }

  // -------------------------------------------------------------------------
  // Result rendering (summary, tables, geometry preview, raw JSON)
  // -------------------------------------------------------------------------
  const GEOM_TYPES = new Set(["Point", "MultiPoint", "LineString", "MultiLineString", "Polygon", "MultiPolygon", "GeometryCollection"]);

  function collectGeoms(value, role, out = [], depth = 0, parent = null) {
    if (!value || typeof value !== "object" || depth > 10 || out.length > 3000) return out;
    if (Array.isArray(value)) {
      value.forEach((v) => collectGeoms(v, role, out, depth + 1, parent));
      return out;
    }
    if (value.type === "FeatureCollection" && Array.isArray(value.features)) {
      value.features.forEach((f) => collectGeoms(f, role, out, depth + 1));
      return out;
    }
    if (value.type === "Feature") {
      if (value.geometry) out.push({ geom: value.geometry, props: value.properties || {}, role });
      return out;
    }
    if (GEOM_TYPES.has(value.type) && (value.coordinates || value.geometries)) {
      out.push({ geom: value, props: parent || {}, role });
      return out;
    }
    for (const v of Object.values(value)) collectGeoms(v, role, out, depth + 1, value);
    return out;
  }

  function flattenGeom(geom) {
    // Returns { points: [[x,y]], lines: [[[x,y]...]], polys: [[ring...]] }
    const acc = { points: [], lines: [], polys: [] };
    const walk = (g) => {
      if (!g) return;
      const c = g.coordinates;
      switch (g.type) {
        case "Point": acc.points.push(c); break;
        case "MultiPoint": acc.points.push(...c); break;
        case "LineString": acc.lines.push(c); break;
        case "MultiLineString": acc.lines.push(...c); break;
        case "Polygon": acc.polys.push(c); break;
        case "MultiPolygon": acc.polys.push(...c); break;
        case "GeometryCollection": (g.geometries || []).forEach(walk); break;
        default: break;
      }
    };
    walk(geom);
    return acc;
  }

  const PALETTE = ["#2e7d32", "#f9a825", "#6d4c41", "#00838f", "#ad1457", "#5e35b1", "#ef6c00", "#558b2f", "#1565c0", "#8d6e63", "#c62828", "#00695c"];

  function categoryOf(item) {
    const p = item.props || {};
    return String(p.farmlndcl ?? p.farmland_class ?? p.farmland_classification ?? p.county_name ?? p.NAME ?? p.musym ?? p.mukey ?? "feature");
  }

  function renderMap(items) {
    const W = 560;
    const H = 380;
    const PAD = 14;
    const flat = items.map((it) => ({ ...it, f: flattenGeom(it.geom) }));
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const visit = (p) => {
      if (!Array.isArray(p) || typeof p[0] !== "number") return;
      minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]);
      minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]);
    };
    for (const it of flat) {
      it.f.points.forEach(visit);
      it.f.lines.forEach((l) => l.forEach(visit));
      it.f.polys.forEach((poly) => poly.forEach((ring) => ring.forEach(visit)));
    }
    if (!Number.isFinite(minX)) return null;
    const kx = Math.cos((((minY + maxY) / 2) * Math.PI) / 180) || 1;
    const dx = Math.max((maxX - minX) * kx, 1e-6);
    const dy = Math.max(maxY - minY, 1e-6);
    const scale = Math.min((W - 2 * PAD) / dx, (H - 2 * PAD) / dy);
    const ox = (W - dx * scale) / 2;
    const oy = (H - dy * scale) / 2;
    const proj = (p) => [ox + (p[0] - minX) * kx * scale, H - oy - (p[1] - minY) * scale];
    const pathOf = (coords, close) => coords.map((p, i) => `${i ? "L" : "M"}${proj(p).map((n) => n.toFixed(1)).join(",")}`).join("") + (close ? "Z" : "");

    const colors = new Map();
    const colorFor = (cat) => {
      if (!colors.has(cat)) colors.set(cat, PALETTE[colors.size % PALETTE.length]);
      return colors.get(cat);
    };

    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("width", W);
    svg.setAttribute("height", H);
    svg.setAttribute("class", "map");
    const add = (tag, attrs, title) => {
      const n = document.createElementNS(NS, tag);
      for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
      if (title) {
        const t = document.createElementNS(NS, "title");
        t.textContent = title;
        n.append(t);
      }
      svg.append(n);
    };

    const ordered = [...flat.filter((i) => i.role === "output"), ...flat.filter((i) => i.role === "input")];
    for (const it of ordered) {
      const isInput = it.role === "input";
      const cat = isInput ? "Input geometry" : categoryOf(it);
      const color = isInput ? "#005ea2" : colorFor(cat);
      const p = it.props || {};
      const title = isInput
        ? "Input geometry"
        : [cat, p.musym && `musym ${p.musym}`, p.mukey && `mukey ${p.mukey}`, p.muname, p.acres !== undefined && `${fmtScalar(p.acres)} ac`]
            .filter(Boolean)
            .join(" | ");
      for (const poly of it.f.polys) {
        add("path", {
          d: poly.map((ring) => pathOf(ring, true)).join(""),
          fill: isInput ? "rgba(0,94,162,0.06)" : color,
          "fill-opacity": isInput ? 1 : 0.55,
          "fill-rule": "evenodd",
          stroke: color,
          "stroke-width": isInput ? 2 : 1,
          "stroke-dasharray": isInput ? "6 4" : "",
        }, title);
      }
      for (const line of it.f.lines) {
        add("path", { d: pathOf(line, false), fill: "none", stroke: color, "stroke-width": isInput ? 2.5 : 2 }, title);
      }
      for (const pt of it.f.points) {
        const [x, y] = proj(pt);
        add("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: 5, fill: color, stroke: "#fff", "stroke-width": 1.5 }, title);
      }
    }

    const legend = el("div", { class: "legend" });
    if (flat.some((i) => i.role === "input")) {
      legend.append(el("div", {}, el("span", { class: "sw", style: "background:rgba(0,94,162,.15);border:2px dashed #005ea2" }), "Input geometry"));
    }
    for (const [cat, color] of colors) legend.append(el("div", {}, el("span", { class: "sw", style: `background:${color}` }), cat));
    legend.append(el("div", { class: "muted small", text: `Extent: ${minX.toFixed(4)}, ${minY.toFixed(4)} to ${maxX.toFixed(4)}, ${maxY.toFixed(4)}` }));
    return el("div", { class: "map-wrap" }, svg, legend);
  }

  function findTables(value, path = "", out = [], depth = 0) {
    if (!value || typeof value !== "object" || depth > 3 || out.length >= 8) return out;
    if (Array.isArray(value)) {
      if (value.length && value.every((r) => r && typeof r === "object" && !Array.isArray(r))) out.push({ path: path || "(root)", rows: value });
      return out;
    }
    if (value.type === "FeatureCollection" && Array.isArray(value.features)) {
      out.push({ path: `${path || "(root)"}.features[].properties`, rows: value.features.map((f) => f.properties || {}) });
      return out;
    }
    for (const [k, v] of Object.entries(value)) findTables(v, path ? `${path}.${k}` : k, out, depth + 1);
    return out;
  }

  function renderTable(rows) {
    const cols = [];
    for (const r of rows.slice(0, 50)) {
      for (const [k, v] of Object.entries(r)) if (isScalar(v) && !cols.includes(k) && cols.length < 14) cols.push(k);
    }
    if (!cols.length) return el("p", { class: "muted small", text: "No scalar columns to tabulate." });
    const table = el(
      "table",
      { class: "grid" },
      el("thead", {}, el("tr", {}, cols.map((c) => el("th", { text: c })))),
      el(
        "tbody",
        {},
        rows.slice(0, 300).map((r) => el("tr", {}, cols.map((c) => el("td", { class: "clip", title: r[c] === undefined ? "" : String(r[c]), text: r[c] === undefined ? "" : fmtScalar(r[c]) })))),
      ),
    );
    const wrap = el("div", { class: "table-wrap" }, table);
    return rows.length > 300 ? el("div", {}, wrap, el("p", { class: "muted small", text: `Showing 300 of ${rows.length} rows.` })) : wrap;
  }

  function renderPayloadSummary(payload) {
    const frag = document.createDocumentFragment();
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return frag;
    const scalars = Object.entries(payload).filter(([k, v]) => isScalar(v) && k !== "regulatory_notice");
    if (scalars.length) {
      frag.append(
        el("dl", { class: "kv" }, scalars.slice(0, 30).map(([k, v]) => el("div", {}, el("dt", { text: k }), el("dd", { text: fmtScalar(v) })))),
      );
    }
    // Nested one-level objects with scalar fields (e.g. land_evaluation, site_assessment summary).
    for (const [k, v] of Object.entries(payload)) {
      if (!v || typeof v !== "object" || Array.isArray(v) || v.type) continue;
      const inner = Object.entries(v).filter(([, iv]) => isScalar(iv));
      if (inner.length < 2) continue;
      frag.append(
        el(
          "details",
          { class: "subsection" },
          el("summary", { text: k }),
          el("dl", { class: "kv" }, inner.slice(0, 30).map(([ik, iv]) => el("div", {}, el("dt", { text: ik }), el("dd", { text: fmtScalar(iv) })))),
        ),
      );
    }
    if (typeof payload.regulatory_notice === "string") frag.append(el("div", { class: "callout", text: payload.regulatory_notice }));
    const lim = payload.limitations || payload.warnings;
    if (Array.isArray(lim) && lim.length) {
      frag.append(
        el(
          "details",
          { class: "subsection" },
          el("summary", { text: `Limitations / warnings (${lim.length})` }),
          el("ul", {}, lim.map((l) => el("li", { text: typeof l === "string" ? l : JSON.stringify(l) }))),
        ),
      );
    }
    return frag;
  }

  function renderToolResult(container, out, args, name) {
    container.innerHTML = "";
    const result = out.result || {};
    const isError = Boolean(result.isError);
    const payload = out.payload;
    container.append(
      el(
        "div",
        { class: "result-head" },
        el("span", { class: `badge ${isError ? "err" : "ok"}`, text: isError ? "TOOL ERROR" : "OK" }),
        el("span", { class: "muted small", text: fmtMs(out.durationMs) }),
        el("button", { class: "btn tiny", text: "Copy payload", onclick: () => copyText(JSON.stringify(payload, null, 2)) }),
        el("button", { class: "btn tiny", text: "Download", onclick: () => downloadJson(`${name}-${Date.now()}`, { arguments: args, result }) }),
      ),
    );
    if (isError) {
      const msg = (result.content || []).map((c) => c.text).filter(Boolean).join("\n");
      container.append(el("div", { class: "callout err prewrap", text: msg || "Tool reported an error." }));
    }
    container.append(renderPayloadSummary(payload));

    const geoms = [...collectGeoms(args, "input"), ...collectGeoms(payload, "output")];
    if (geoms.length) {
      const map = renderMap(geoms);
      if (map) container.append(el("details", { class: "subsection", open: true }, el("summary", { text: `Geometry preview (${geoms.length})` }), map));
    }

    for (const t of findTables(payload)) {
      container.append(el("details", { class: "subsection", open: true }, el("summary", { text: `${t.path} (${t.rows.length})` }), renderTable(t.rows)));
    }
    container.append(el("details", { class: "subsection", open: !findTables(payload).length }, el("summary", { text: "Payload JSON" }), jsonBlock(payload)));
    container.append(el("details", { class: "subsection" }, el("summary", { text: "Raw MCP CallToolResult" }), jsonBlock(result)));
  }

  function renderErrorResult(container, err) {
    container.innerHTML = "";
    container.append(
      el("div", { class: "result-head" }, el("span", { class: "badge err", text: "REQUEST FAILED" })),
      el("div", { class: "callout err prewrap", text: err.message }),
    );
    if (err.data) container.append(jsonBlock(err.data));
  }

  // -------------------------------------------------------------------------
  // Tools tab
  // -------------------------------------------------------------------------
  function renderToolList() {
    const filter = $("#toolFilter").value.toLowerCase();
    const list = $("#toolList");
    list.innerHTML = "";
    for (const tool of state.tools) {
      if (filter && !tool.name.toLowerCase().includes(filter) && !(tool.description || "").toLowerCase().includes(filter)) continue;
      const firstLine = (tool.description || "").split("\n")[0];
      list.append(
        el(
          "li",
          { class: state.currentTool?.name === tool.name ? "active" : "", onclick: () => selectTool(tool.name) },
          tool.name,
          el("span", { class: "sub", text: firstLine }),
        ),
      );
    }
    if (!state.tools.length) list.append(el("li", { class: "muted", text: "No tools (not connected?)" }));
  }

  function selectTool(name, args) {
    const tool = state.tools.find((t) => t.name === name);
    if (!tool) {
      toast(`Tool '${name}' is not available on the connected server`, true);
      return;
    }
    state.currentTool = tool;
    renderToolList();
    $("#toolEmpty").classList.add("hidden");
    $("#toolDetail").classList.remove("hidden");
    $("#toolName").textContent = tool.name;
    $("#toolDescription").textContent = tool.description || "(no description)";
    $("#toolSchema").innerHTML = highlightJson(tool.inputSchema || {});
    $("#toolResult").innerHTML = "";
    $("#toolRunStatus").textContent = "";

    const presetSel = $("#toolPreset");
    presetSel.innerHTML = "";
    presetSel.append(el("option", { value: "", text: "(defaults)" }));
    (state.presets[`tool:${name}`] || []).forEach((p, i) => presetSel.append(el("option", { value: String(i), text: p.label })));

    $("#toolJsonMode").checked = false;
    $("#toolJson").classList.add("hidden");
    $("#toolForm").classList.remove("hidden");
    buildArgForm($("#toolForm"), tool.inputSchema, args || {});
    if (args) $("#toolPreset").value = "";
  }

  function applyToolPreset() {
    const tool = state.currentTool;
    if (!tool) return;
    const idx = $("#toolPreset").value;
    const preset = idx === "" ? null : (state.presets[`tool:${tool.name}`] || [])[Number(idx)];
    const args = preset ? preset.arguments : {};
    if ($("#toolJsonMode").checked) $("#toolJson").value = JSON.stringify(args, null, 2);
    buildArgForm($("#toolForm"), tool.inputSchema, args);
  }

  function toggleJsonMode() {
    const on = $("#toolJsonMode").checked;
    if (on) {
      $("#toolJson").value = JSON.stringify(collectArgs($("#toolForm")).args, null, 2);
    } else {
      try {
        const parsed = JSON.parse($("#toolJson").value || "{}");
        buildArgForm($("#toolForm"), state.currentTool.inputSchema, parsed);
      } catch (e) {
        toast(`Invalid JSON: ${e.message}`, true);
        $("#toolJsonMode").checked = true;
        return;
      }
    }
    $("#toolJson").classList.toggle("hidden", !on);
    $("#toolForm").classList.toggle("hidden", on);
  }

  async function runTool() {
    const tool = state.currentTool;
    if (!tool) return;
    let args;
    if ($("#toolJsonMode").checked) {
      try {
        args = JSON.parse($("#toolJson").value || "{}");
      } catch (e) {
        toast(`Invalid JSON: ${e.message}`, true);
        return;
      }
    } else {
      const { args: a, errors } = collectArgs($("#toolForm"));
      if (errors.length) {
        toast(errors.join("; "), true);
        return;
      }
      args = a;
    }
    const timeoutMs = Math.max(5, Number($("#toolTimeout").value) || 180) * 1000;
    const btn = $("#btnRunTool");
    btn.disabled = true;
    const started = Date.now();
    const ticker = setInterval(() => ($("#toolRunStatus").textContent = `Running... ${((Date.now() - started) / 1000).toFixed(0)} s`), 500);
    try {
      const out = await api(`/api/tools/${encodeURIComponent(tool.name)}/call`, { method: "POST", body: { arguments: args, timeoutMs } });
      renderToolResult($("#toolResult"), out, args, tool.name);
      $("#toolRunStatus").textContent = `Completed in ${fmtMs(out.durationMs)}`;
    } catch (err) {
      renderErrorResult($("#toolResult"), err);
      $("#toolRunStatus").textContent = "Failed";
    } finally {
      clearInterval(ticker);
      btn.disabled = false;
    }
  }

  // -------------------------------------------------------------------------
  // Resources tab
  // -------------------------------------------------------------------------
  function renderResourceList() {
    const list = $("#resourceList");
    list.innerHTML = "";
    for (const r of state.resources) {
      list.append(el("li", { onclick: (e) => readResource(r.uri, e.currentTarget) }, r.name || r.uri, el("span", { class: "sub", text: r.uri })));
    }
    for (const t of state.templates) {
      list.append(
        el(
          "li",
          {
            onclick: () => {
              const uri = window.prompt(`Resolve template ${t.uriTemplate}`, t.uriTemplate);
              if (uri) readResource(uri);
            },
          },
          `${t.name || t.uriTemplate} (template)`,
          el("span", { class: "sub", text: t.uriTemplate }),
        ),
      );
    }
    if (!state.resources.length && !state.templates.length) list.append(el("li", { class: "muted", text: "No resources" }));
  }

  async function readResource(uri, li) {
    $$("#resourceList li").forEach((n) => n.classList.remove("active"));
    li?.classList.add("active");
    $("#resourceEmpty").classList.add("hidden");
    const box = $("#resourceResult");
    box.innerHTML = "";
    box.append(el("p", { class: "muted", text: `Reading ${uri}...` }));
    try {
      const out = await api(`/api/resources/read?uri=${encodeURIComponent(uri)}`);
      box.innerHTML = "";
      box.append(
        el(
          "div",
          { class: "result-head" },
          el("h2", { text: uri }),
          el("span", { class: "badge ok", text: "OK" }),
          el("span", { class: "muted small", text: fmtMs(out.durationMs) }),
        ),
      );
      for (const c of out.result.contents || []) {
        box.append(el("p", { class: "muted small", text: `${c.uri || ""} ${c.mimeType ? `(${c.mimeType})` : ""}` }));
        if (c.parsed !== undefined) {
          box.append(renderPayloadSummary(c.parsed));
          for (const t of findTables(c.parsed)) {
            box.append(el("details", { class: "subsection", open: true }, el("summary", { text: `${t.path} (${t.rows.length})` }), renderTable(t.rows)));
          }
          box.append(el("details", { class: "subsection", open: true }, el("summary", { text: "JSON" }), jsonBlock(c.parsed)));
        } else if (c.text !== undefined) {
          box.append(el("pre", { class: "log prewrap", text: c.text }));
        } else {
          box.append(el("p", { class: "muted", text: `Binary content (${(c.blob || "").length} base64 chars)` }));
        }
      }
    } catch (err) {
      renderErrorResult(box, err);
    }
  }

  // -------------------------------------------------------------------------
  // Prompts tab
  // -------------------------------------------------------------------------
  function renderPromptList() {
    const list = $("#promptList");
    list.innerHTML = "";
    for (const p of state.prompts) {
      list.append(
        el(
          "li",
          { class: state.currentPrompt?.name === p.name ? "active" : "", onclick: () => selectPrompt(p.name) },
          p.name,
          el("span", { class: "sub", text: (p.description || "").split("\n")[0] }),
        ),
      );
    }
    if (!state.prompts.length) list.append(el("li", { class: "muted", text: "No prompts" }));
  }

  function promptSchema(prompt) {
    const properties = {};
    const required = [];
    for (const a of prompt.arguments || []) {
      properties[a.name] = { type: "string", description: a.description || "" };
      if (a.required) required.push(a.name);
    }
    return { type: "object", properties, required };
  }

  function selectPrompt(name, args) {
    const prompt = state.prompts.find((p) => p.name === name);
    if (!prompt) {
      toast(`Prompt '${name}' is not available on the connected server`, true);
      return;
    }
    state.currentPrompt = prompt;
    renderPromptList();
    $("#promptEmpty").classList.add("hidden");
    $("#promptDetail").classList.remove("hidden");
    $("#promptName").textContent = prompt.name;
    $("#promptDescription").textContent = prompt.description || "";
    $("#promptResult").innerHTML = "";
    const sel = $("#promptPreset");
    sel.innerHTML = "";
    sel.append(el("option", { value: "", text: "(defaults)" }));
    (state.presets[`prompt:${name}`] || []).forEach((p, i) => sel.append(el("option", { value: String(i), text: p.label })));
    buildArgForm($("#promptForm"), promptSchema(prompt), args || {});
  }

  function applyPromptPreset() {
    const p = state.currentPrompt;
    if (!p) return;
    const idx = $("#promptPreset").value;
    const preset = idx === "" ? null : (state.presets[`prompt:${p.name}`] || [])[Number(idx)];
    buildArgForm($("#promptForm"), promptSchema(p), preset ? preset.arguments : {});
  }

  function renderPromptMessages(container, out) {
    container.innerHTML = "";
    const msgs = out.result?.messages || [];
    container.append(
      el(
        "div",
        { class: "result-head" },
        el("span", { class: "badge ok", text: "RENDERED" }),
        el("span", { class: "muted small", text: `${msgs.length} message(s), ${fmtMs(out.durationMs)}` }),
        el("button", { class: "btn tiny", text: "Copy text", onclick: () => copyText(msgs.map((m) => m.content?.text || "").join("\n\n")) }),
      ),
    );
    if (out.result?.description) container.append(el("p", { class: "muted", text: out.result.description }));
    for (const m of msgs) {
      const body = m.content?.type === "text" ? m.content.text : JSON.stringify(m.content, null, 2);
      container.append(el("div", { class: "message" }, el("div", { class: "role", text: m.role }), el("div", { class: "body", text: body })));
    }
    container.append(el("details", { class: "subsection" }, el("summary", { text: "Raw GetPromptResult" }), jsonBlock(out.result)));
  }

  async function runPrompt() {
    const p = state.currentPrompt;
    if (!p) return;
    const { args, errors } = collectArgs($("#promptForm"));
    if (errors.length) {
      toast(errors.join("; "), true);
      return;
    }
    $("#promptRunStatus").textContent = "Rendering...";
    try {
      const out = await api(`/api/prompts/${encodeURIComponent(p.name)}`, { method: "POST", body: { arguments: args } });
      renderPromptMessages($("#promptResult"), out);
      $("#promptRunStatus").textContent = "";
    } catch (err) {
      renderErrorResult($("#promptResult"), err);
      $("#promptRunStatus").textContent = "Failed";
    }
  }

  // -------------------------------------------------------------------------
  // Eval cases tab
  // -------------------------------------------------------------------------
  async function loadEvals() {
    try {
      const [data, presets] = await Promise.all([api("/api/eval-cases"), api("/api/presets")]);
      state.evals = data.test_cases || [];
      state.presets = presets || {};
      $("#countEvals").textContent = state.evals.length;
      $("#evalSource").textContent = `${data.source}${data.version ? ` (v${data.version})` : ""} - ${data.description || ""}`;
      const cats = [...new Set(state.evals.map((c) => c.category))];
      const sel = $("#evalFilter");
      sel.innerHTML = "";
      sel.append(el("option", { value: "", text: "All categories" }));
      cats.forEach((c) => sel.append(el("option", { value: c, text: c })));
      renderEvalTable();
    } catch (err) {
      $("#evalSource").textContent = `Could not load eval cases: ${err.message}`;
    }
  }

  const filteredEvals = () => state.evals.filter((c) => !$("#evalFilter").value || c.category === $("#evalFilter").value);

  function evalStatusBadge(id) {
    const r = state.evalResults[id];
    if (!r) return el("span", { class: "badge neutral", text: "not run" });
    if (r.running) return el("span", { class: "badge warn", text: "running" });
    if (r.passed) return el("span", { class: "badge ok", text: "pass" });
    return el("span", { class: "badge err", text: r.isError ? "error" : "fail" });
  }

  function renderEvalTable() {
    const tbody = $("#evalTable tbody");
    tbody.innerHTML = "";
    for (const tc of filteredEvals()) {
      const r = state.evalResults[tc.id];
      tbody.append(
        el(
          "tr",
          { class: state.selectedEval === tc.id ? "selected" : "", onclick: () => selectEval(tc.id) },
          el("td", { class: "mono", text: tc.id }),
          el("td", { text: tc.category }),
          el("td", { class: "mono", text: `${tc.target_type}: ${tc.target_name}` }),
          el("td", { class: "clip", title: tc.user_prompt, text: tc.user_prompt }),
          el("td", {}, evalStatusBadge(tc.id)),
          el("td", { class: "mono", text: r && !r.running ? fmtMs(r.durationMs) : "" }),
          el(
            "td",
            { class: "inline" },
            el("button", { class: "btn tiny", text: "Run", onclick: (e) => (e.stopPropagation(), runEval(tc.id)) }),
            el("button", { class: "btn tiny", text: "Open", onclick: (e) => (e.stopPropagation(), openEval(tc)) }),
          ),
        ),
      );
    }
    renderEvalSummary();
  }

  function renderEvalSummary() {
    const cases = filteredEvals();
    const results = cases.map((c) => state.evalResults[c.id]).filter((r) => r && !r.running);
    const passed = results.filter((r) => r.passed).length;
    const errored = results.filter((r) => !r.passed && r.isError).length;
    const failed = results.length - passed - errored;
    const total = results.reduce((s, r) => s + (r.durationMs || 0), 0);
    const box = $("#evalSummary");
    box.innerHTML = "";
    box.append(
      el("span", { class: "stat", text: `${cases.length} cases` }),
      el("span", { class: "stat", text: `${results.length} run` }),
      el("span", { class: "stat", style: "color:var(--ok)", text: `${passed} pass` }),
      el("span", { class: "stat", style: "color:var(--err)", text: `${failed} fail` }),
      el("span", { class: "stat", style: "color:var(--warn)", text: `${errored} error` }),
      el("span", { class: "stat", text: `total ${fmtMs(total)}` }),
      results.length ? el("button", { class: "btn tiny", text: "Download results", onclick: () => downloadJson(`eval-results-${Date.now()}`, results) }) : null,
    );
  }

  function selectEval(id) {
    state.selectedEval = id;
    renderEvalTable();
    renderEvalDetail(id);
  }

  function renderEvalDetail(id) {
    const tc = state.evals.find((c) => c.id === id);
    const box = $("#evalDetail");
    box.innerHTML = "";
    if (!tc) return;
    const r = state.evalResults[id];
    box.append(
      el("h3", { text: `${tc.id} - ${tc.category}` }),
      el("p", { class: "prewrap", text: tc.user_prompt }),
      el("p", { class: "small" }, el("strong", { text: "Expected tools: " }), (tc.expected_tools || []).join(", ") || "(none)"),
      el("div", { class: "small" }, el("strong", { text: "Expected keywords: " }),
        (tc.expected_keywords || []).map((k) => {
          const cls = !r || r.running ? "kw" : r.keywords?.found?.includes(k) ? "kw hit" : "kw miss";
          return el("span", { class: cls, text: k });
        }),
      ),
      el("details", { class: "subsection", open: true }, el("summary", { text: "Derived invocation" }), jsonBlock(tc.invocation)),
    );
    if (!r || r.running) return;
    if (r.error) box.append(el("div", { class: "callout err prewrap", text: r.error.message }));
    const out = r.output;
    if (!out) return;
    const holder = el("div", {});
    if (r.invocation.kind === "tool") renderToolResult(holder, out, r.invocation.arguments, tc.target_name);
    else if (r.invocation.kind === "prompt") renderPromptMessages(holder, out);
    else holder.append(jsonBlock(out.result));
    box.append(el("details", { class: "subsection", open: true }, el("summary", { text: "Response" }), holder));
  }

  async function runEval(id) {
    state.evalResults[id] = { running: true };
    renderEvalTable();
    if (state.selectedEval === id) renderEvalDetail(id);
    const timeoutMs = Math.max(5, Number($("#toolTimeout").value) || 180) * 1000;
    try {
      state.evalResults[id] = await api(`/api/eval-cases/${encodeURIComponent(id)}/run`, { method: "POST", body: { timeoutMs } });
    } catch (err) {
      state.evalResults[id] = { id, passed: false, isError: true, error: { message: err.message }, keywords: { found: [], missing: [] } };
    }
    renderEvalTable();
    if (state.selectedEval === id) renderEvalDetail(id);
  }

  async function runAllEvals() {
    if (!state.status?.connected) {
      toast("Connect to the MCP server first", true);
      return;
    }
    state.stopEvals = false;
    $("#btnRunAllEvals").disabled = true;
    $("#btnStopEvals").disabled = false;
    try {
      for (const tc of filteredEvals()) {
        if (state.stopEvals) break;
        await runEval(tc.id);
      }
    } finally {
      $("#btnRunAllEvals").disabled = false;
      $("#btnStopEvals").disabled = true;
      toast(state.stopEvals ? "Eval run stopped" : "Eval run complete");
    }
  }

  function openEval(tc) {
    const inv = tc.invocation;
    if (inv.kind === "tool") {
      showTab("tools");
      selectTool(inv.name, inv.arguments);
    } else if (inv.kind === "prompt") {
      showTab("prompts");
      selectPrompt(inv.name, inv.arguments);
    } else {
      showTab("resources");
      readResource(inv.uri);
    }
  }

  // -------------------------------------------------------------------------
  // History & server tabs
  // -------------------------------------------------------------------------
  async function refreshHistory() {
    const { history } = await api("/api/history");
    const tbody = $("#historyTable tbody");
    tbody.innerHTML = "";
    for (const h of history) {
      tbody.append(
        el(
          "tr",
          {},
          el("td", { class: "mono", text: new Date(h.ts).toLocaleTimeString() }),
          el("td", { text: h.kind }),
          el("td", { class: "mono", text: h.name }),
          el("td", {}, el("span", { class: `badge ${h.ok ? "ok" : "err"}`, text: h.ok ? "ok" : "error" })),
          el("td", { class: "mono", text: fmtMs(h.durationMs) }),
          el("td", { class: "mono clip", title: h.error || JSON.stringify(h.arguments || {}), text: h.error || JSON.stringify(h.arguments || {}) }),
        ),
      );
    }
    if (!history.length) tbody.append(el("tr", {}, el("td", { colspan: 6, class: "muted", text: "No runs yet." })));
  }

  async function refreshServer() {
    await refreshStatus();
    const s = state.status || {};
    const { stderrTail, instructions, ...rest } = s;
    $("#serverStatus").innerHTML = highlightJson(rest);
    $("#serverInstructions").textContent = instructions || "(none)";
    $("#serverStderr").textContent = (stderrTail || []).map((l) => `${l.ts}  ${l.line}`).join("\n") || "(empty)";
  }

  async function checkServerRoutes() {
    $("#serverRoutes").textContent = "Checking...";
    try {
      $("#serverRoutes").innerHTML = highlightJson(await api("/api/server-routes"));
    } catch (err) {
      $("#serverRoutes").textContent = err.message;
    }
  }

  // -------------------------------------------------------------------------
  // Wiring
  // -------------------------------------------------------------------------
  function wire() {
    $$(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
    $("#connMode").addEventListener("change", updateModeVisibility);
    $("#connectForm").addEventListener("submit", connect);
    $("#btnDisconnect").addEventListener("click", disconnect);
    $("#toolFilter").addEventListener("input", renderToolList);
    $("#toolPreset").addEventListener("change", applyToolPreset);
    $("#toolJsonMode").addEventListener("change", toggleJsonMode);
    $("#btnRunTool").addEventListener("click", runTool);
    $("#promptPreset").addEventListener("change", applyPromptPreset);
    $("#btnRunPrompt").addEventListener("click", runPrompt);
    $("#evalFilter").addEventListener("change", renderEvalTable);
    $("#btnRunAllEvals").addEventListener("click", runAllEvals);
    $("#btnStopEvals").addEventListener("click", () => (state.stopEvals = true));
    $("#btnRefreshHistory").addEventListener("click", refreshHistory);
    $("#btnClearHistory").addEventListener("click", async () => {
      await api("/api/history", { method: "DELETE" });
      refreshHistory();
    });
    $("#btnRefreshServer").addEventListener("click", refreshServer);
    $("#btnServerRoutes").addEventListener("click", checkServerRoutes);
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && $("#panel-tools").classList.contains("active")) runTool();
    });
  }

  async function init() {
    wire();
    try {
      await loadConfig();
    } catch (err) {
      toast(`Harness backend unreachable: ${err.message}`, true);
      return;
    }
    await loadEvals();
    await refreshStatus(); // loads the tool/resource/prompt catalog when already connected
    renderConnection();
    setInterval(refreshStatus, 10000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
