// PPO Model Comparison -- vanilla JS frontend, no framework/build step.
// Talks to the FastAPI backend (server.py) via fetch(); polls /api/status
// every second while a comparison is running.

const EST_MIN_PER_EPISODE = 2.5;
const MAX_WORKERS = 10;

let registry = [];
let checkedPaths = new Set();
let checkedBaselines = new Set();
let seedMode = "random";
let manualSeeds = [];
let scenario = "Low";
let pollTimer = null;

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

// ---------------- Models ----------------

async function loadModels() {
  const res = await fetch("/api/models");
  registry = await res.json();
  if (checkedPaths.size === 0) {
    const def = registry.find((m) => m.name === "V8_final_6M");
    if (def) checkedPaths.add(def.path);
  }
  renderModels();
  updateEstimate();
}

function renderModels() {
  const container = document.getElementById("models-list");
  container.innerHTML = "";
  registry.forEach((m) => {
    const row = document.createElement("div");
    row.className = "model-row";
    const checked = checkedPaths.has(m.path) ? "checked" : "";
    row.innerHTML = `
      <label class="model-label">
        <input type="checkbox" data-path="${escapeHtml(m.path)}" ${checked}>
        <span>${escapeHtml(m.name)}</span>
      </label>
      <span class="model-path muted">${escapeHtml(m.path)}</span>
      <button class="remove-btn" data-path="${escapeHtml(m.path)}">x</button>
    `;
    container.appendChild(row);
  });
  container.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", () => {
      const p = cb.dataset.path;
      if (cb.checked) checkedPaths.add(p);
      else checkedPaths.delete(p);
      updateEstimate();
    });
  });
  container.querySelectorAll(".remove-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch("/api/models", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: btn.dataset.path }),
      });
      checkedPaths.delete(btn.dataset.path);
      await loadModels();
    });
  });
}

document.getElementById("add-model-btn").addEventListener("click", async () => {
  const input = document.getElementById("model-path-input");
  const path = input.value.trim();
  if (!path) return;
  await fetch("/api/models", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  input.value = "";
  await loadModels();
});

// ---------------- Baselines ----------------

async function loadBaselines() {
  const res = await fetch("/api/baselines");
  const names = await res.json();
  const container = document.getElementById("baselines-list");
  container.innerHTML = "";
  names.forEach((name) => {
    const row = document.createElement("div");
    row.className = "model-row";
    row.innerHTML = `
      <label class="model-label">
        <input type="checkbox" data-name="${escapeHtml(name)}">
        <span>${escapeHtml(name)}</span>
      </label>
    `;
    container.appendChild(row);
  });
  container.querySelectorAll("input[type=checkbox]").forEach((cb) => {
    cb.addEventListener("change", () => {
      if (cb.checked) checkedBaselines.add(cb.dataset.name);
      else checkedBaselines.delete(cb.dataset.name);
      updateEstimate();
    });
  });
}

// ---------------- Seed mode / scenario toggles ----------------

document.querySelectorAll("#seed-mode-toggle .seg-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    seedMode = btn.dataset.value;
    document
      .querySelectorAll("#seed-mode-toggle .seg-btn")
      .forEach((b) => b.classList.toggle("active", b === btn));
    document.getElementById("random-seed-controls").style.display =
      seedMode === "random" ? "" : "none";
    document.getElementById("manual-seed-controls").style.display =
      seedMode === "manual" ? "" : "none";
    updateEstimate();
  });
});

document.getElementById("seed-count").addEventListener("input", updateEstimate);

document.getElementById("add-seed-btn").addEventListener("click", () => {
  const input = document.getElementById("seed-value-input");
  const val = parseInt(input.value, 10);
  if (Number.isNaN(val)) return;
  manualSeeds.push(val);
  input.value = "";
  renderSeedChips();
  updateEstimate();
});

function renderSeedChips() {
  const container = document.getElementById("seed-chips");
  container.innerHTML = "";
  manualSeeds.forEach((s, idx) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.innerHTML = `<span>${s}</span><button data-idx="${idx}">x</button>`;
    container.appendChild(chip);
  });
  container.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      manualSeeds.splice(parseInt(btn.dataset.idx, 10), 1);
      renderSeedChips();
      updateEstimate();
    });
  });
}

document.querySelectorAll("#scenario-toggle .seg-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    scenario = btn.dataset.value;
    document
      .querySelectorAll("#scenario-toggle .seg-btn")
      .forEach((b) => b.classList.toggle("active", b === btn));
    updateEstimate();
  });
});

function currentScenarios() {
  return scenario === "All" ? ["Low", "Medium", "High"] : [scenario];
}

function currentSeedCount() {
  if (seedMode === "random") {
    return parseInt(document.getElementById("seed-count").value, 10) || 0;
  }
  return manualSeeds.length;
}

// ---------------- Estimate ----------------

function updateEstimate() {
  const nControllers = checkedPaths.size + checkedBaselines.size;
  const nSeeds = currentSeedCount();
  const scens = currentScenarios();
  const nEpisodes = nControllers * nSeeds * scens.length;
  const watchLive = document.getElementById("watch-live-checkbox").checked;
  let etaMin = 0,
    workers = 1;
  if (nEpisodes > 0) {
    workers = watchLive ? 1 : Math.max(1, Math.min(MAX_WORKERS, nEpisodes));
    etaMin = (nEpisodes * EST_MIN_PER_EPISODE) / workers;
  }
  document.getElementById("estimate-text").textContent =
    `${nEpisodes} episodes  (${nControllers} models/baselines x ${nSeeds} seeds x ${scens.length} scenarios)` +
    `  ~${etaMin.toFixed(1)} min est. (${workers} workers)`;
}

document.getElementById("watch-live-checkbox").addEventListener("change", updateEstimate);

// ---------------- Start / poll ----------------

function randomSeeds(n) {
  const set = new Set();
  while (set.size < n) {
    set.add(1 + Math.floor(Math.random() * 999999));
  }
  return Array.from(set);
}

document.getElementById("start-btn").addEventListener("click", async () => {
  const statusMsg = document.getElementById("status-message");
  const models = Array.from(checkedPaths);
  const baselines = Array.from(checkedBaselines);
  if (models.length === 0 && baselines.length === 0) {
    statusMsg.textContent = "Select at least one model or baseline.";
    return;
  }
  let seedList = seedMode === "manual" ? manualSeeds.slice() : randomSeeds(currentSeedCount());
  if (seedList.length === 0) {
    statusMsg.textContent = "Add at least one seed.";
    return;
  }
  const scenarios = currentScenarios();
  const watchLive = document.getElementById("watch-live-checkbox").checked;
  if (watchLive && (seedList.length !== 1 || scenarios.length !== 1)) {
    statusMsg.textContent =
      "Watch Live requires exactly 1 seed and 1 specific scenario (not \"All\").";
    return;
  }

  statusMsg.textContent = "";
  const res = await fetch("/api/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ models, seeds: seedList, scenarios, baselines, watch_live: watchLive }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    statusMsg.textContent = "Error: " + (err.detail || res.statusText);
    return;
  }
  document.getElementById("start-btn").disabled = true;
  document.getElementById("progress-wrap").style.display = "";
  setProgress(0, 1);
  startPolling();
});

function setProgress(done, total) {
  const pct = total > 0 ? (done / total) * 100 : 0;
  document.getElementById("progress-fill").style.width = pct + "%";
  document.getElementById("progress-text").textContent = `${done}/${total} episodes done`;
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollStatus, 1000);
}

async function pollStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();
  setProgress(data.done, data.total);
  const statusMsg = document.getElementById("status-message");
  const currentTaskText = document.getElementById("current-task-text");
  currentTaskText.textContent = data.current ? `Now running: ${data.current}` : "";
  if (data.warnings && data.warnings.length > 0) {
    statusMsg.textContent = `${data.warnings.length} warning(s) -- see browser console`;
    console.warn("Comparison warnings:", data.warnings);
  }
  if (data.status === "done") {
    clearInterval(pollTimer);
    document.getElementById("start-btn").disabled = false;
    statusMsg.textContent = "Done.";
    currentTaskText.textContent = "";
    renderResults(data.results);
  } else if (data.status === "error") {
    clearInterval(pollTimer);
    document.getElementById("start-btn").disabled = false;
    statusMsg.textContent = "ERROR: " + data.error;
    currentTaskText.textContent = "";
  }
}

// ---------------- Results ----------------

function formatNum(v) {
  if (typeof v !== "number") return v;
  return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function buildTable(scenarioData) {
  const { seed_columns, rows } = scenarioData;
  const table = document.createElement("table");
  table.className = "results-table";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  ["Model", ...seed_columns.map((s) => "Seed " + s), "Average"].forEach((h) => {
    const th = document.createElement("th");
    th.textContent = h;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const sorted = rows.slice().sort((a, b) => a.Average - b.Average);
  const winnerModel = sorted.length > 0 ? sorted[0].model : null;
  sorted.forEach((row) => {
    const tr = document.createElement("tr");
    if (row.model === winnerModel) tr.classList.add("winner-row");
    const cells = [row.model, ...seed_columns.map((s) => formatNum(row[s])), formatNum(row.Average)];
    cells.forEach((c) => {
      const td = document.createElement("td");
      td.textContent = c;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

function buildBarChart(scenarioData) {
  const { rows } = scenarioData;
  const sorted = rows.slice().sort((a, b) => a.Average - b.Average);
  const winnerModel = sorted.length > 0 ? sorted[0].model : null;
  const maxVal = Math.max(...sorted.map((r) => r.Average), 0.0001);

  const chart = document.createElement("div");
  chart.className = "bar-chart";
  sorted.forEach((row) => {
    const barRow = document.createElement("div");
    barRow.className = "bar-row";

    const label = document.createElement("div");
    label.className = "bar-label";
    label.textContent = row.model;

    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill" + (row.model === winnerModel ? " bar-fill-winner" : "");
    fill.style.width = (row.Average / maxVal) * 100 + "%";
    track.appendChild(fill);

    const value = document.createElement("div");
    value.className = "bar-value";
    value.textContent = formatNum(row.Average);

    barRow.appendChild(label);
    barRow.appendChild(track);
    barRow.appendChild(value);
    chart.appendChild(barRow);
  });
  return chart;
}

function renderResults(results) {
  const container = document.getElementById("results-content");
  container.innerHTML = "";
  container.classList.remove("fade-in");
  void container.offsetWidth; // restart the animation even if called twice in a row
  container.classList.add("fade-in");
  if (!results) return;

  const tabBar = document.createElement("div");
  tabBar.className = "tab-bar";
  const panels = document.createElement("div");

  Object.keys(results).forEach((scen, i) => {
    const panel = document.createElement("div");
    panel.className = "tab-panel";
    panel.style.display = i === 0 ? "" : "none";
    panel.appendChild(buildTable(results[scen]));
    const chartTitle = document.createElement("h3");
    chartTitle.className = "bar-chart-title";
    chartTitle.textContent = "Average wait time (seconds)";
    panel.appendChild(chartTitle);
    panel.appendChild(buildBarChart(results[scen]));
    panels.appendChild(panel);

    const tabBtn = document.createElement("button");
    tabBtn.className = "tab-btn" + (i === 0 ? " active" : "");
    tabBtn.textContent = scen;
    tabBtn.addEventListener("click", () => {
      tabBar.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      tabBtn.classList.add("active");
      panels.querySelectorAll(".tab-panel").forEach((p) => (p.style.display = "none"));
      panel.style.display = "";
    });
    tabBar.appendChild(tabBtn);
  });

  container.appendChild(tabBar);
  container.appendChild(panels);
}

loadModels();
loadBaselines();
