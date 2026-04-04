const state = {
  dashboard: null,
  activePreviewKey: "features",
  pollingTimer: null,
};

const previewOrder = [
  ["features", "Features"],
  ["benchmarks", "Benchmarks"],
  ["selection_dataset", "Selection Dataset"],
  ["evaluation", "Evaluation"],
  ["instances", "Instances"],
];

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("realInstanceForm").addEventListener("submit", handleRealInstanceLoad);
  document.getElementById("syntheticPreviewForm").addEventListener("submit", handleSyntheticPreview);
  document.getElementById("demoPipelineForm").addEventListener("submit", handleDemoRun);
  document.getElementById("refreshButton").addEventListener("click", loadDashboardState);
  loadDashboardState().catch((error) => {
    renderTransientStatus("Dashboard load failed", error.message || String(error), "error");
  });
});

async function loadDashboardState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.dashboard = payload;
  if (!state.dashboard.defaults) {
    return;
  }

  hydrateControls(payload);
  renderDashboard();

  if (payload.run_state?.is_running) {
    startPolling();
  } else {
    stopPolling();
  }
}

async function handleRealInstanceLoad(event) {
  event.preventDefault();
  const relativePath = document.getElementById("realInstancePath").value;
  await runAction("/api/load-real-instance", { relative_path: relativePath });
}

async function handleSyntheticPreview(event) {
  event.preventDefault();
  const payload = {
    difficulty_level: document.getElementById("syntheticDifficulty").value,
    random_seed: Number(document.getElementById("previewSeed").value || 42),
  };
  await runAction("/api/generate-synthetic-instance", payload);
}

async function handleDemoRun(event) {
  event.preventDefault();
  const payload = {
    instance_count: Number(document.getElementById("instanceCount").value || 6),
    random_seed: Number(document.getElementById("randomSeed").value || 42),
    time_limit_seconds: Number(document.getElementById("timeLimit").value || 1),
  };
  await runAction("/api/bootstrap-demo", payload);
}

async function runAction(url, payload) {
  toggleBusy(true);
  startPolling();

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.error || "Dashboard request failed.");
    }

    state.dashboard = result;
    hydrateControls(result);
    renderDashboard();
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    renderTransientStatus("Dashboard action failed", message, "error");
  } finally {
    toggleBusy(false);
    await loadDashboardState();
  }
}

function hydrateControls(dashboard) {
  const defaults = dashboard.defaults || {};
  const modeControls = dashboard.mode_controls || {};

  document.getElementById("instanceCount").value = defaults.instance_count ?? 6;
  document.getElementById("randomSeed").value = defaults.random_seed ?? 42;
  document.getElementById("timeLimit").value = defaults.time_limit_seconds ?? 1;
  document.getElementById("previewSeed").value = defaults.random_seed ?? 42;

  populateSelect(
    document.getElementById("realInstancePath"),
    modeControls.real?.available_instances || [],
    (item) => item.relative_path,
    (item) => item.relative_path,
  );
  populateSelect(
    document.getElementById("syntheticDifficulty"),
    (modeControls.synthetic?.difficulty_levels || []).map((value) => ({ value })),
    (item) => item.value,
    (item) => item.value,
    defaults.synthetic_difficulty || "medium",
  );

  const realInstanceCount = modeControls.real?.instance_count || 0;
  document.getElementById("realModeHint").textContent = realInstanceCount
    ? `${realInstanceCount} real XML files available under ${modeControls.real.instance_folder}.`
    : `No real XML files found under ${modeControls.real?.instance_folder || "data/raw/real"}.`;
}

function populateSelect(select, items, getValue, getLabel, selectedValue) {
  const previousValue = selectedValue || select.value;
  if (!items.length) {
    select.innerHTML = `<option value="">No instances available</option>`;
    select.disabled = true;
    return;
  }

  select.disabled = false;
  select.innerHTML = items
    .map((item) => {
      const value = getValue(item);
      const label = getLabel(item);
      const isSelected = value === previousValue ? " selected" : "";
      return `<option value="${escapeHtml(value)}"${isSelected}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function renderDashboard() {
  const dashboard = state.dashboard;
  if (!dashboard) {
    return;
  }

  renderScope(dashboard.dashboard_scope);
  renderStatusBanner(dashboard.run_state, dashboard.overview, dashboard.instance_inspector);
  renderInstanceInspector(dashboard.instance_inspector);
  renderStatsGrid(dashboard.overview, dashboard.training, dashboard.evaluation);
  renderTable("solverLeaderboard", dashboard.solver_leaderboard);
  renderBarList("solverDistribution", dashboard.best_solver_distribution, "count");
  renderBarList("featureImportance", dashboard.feature_importance, "importance");
  renderTable("instanceCatalog", dashboard.instance_catalog);
  renderArtifacts(dashboard.artifacts);
  renderPreviewTabs(dashboard.previews);
  renderPreviewTable();
}

function renderScope(scope) {
  document.getElementById("purposeText").textContent = scope?.purpose || "";
  document.getElementById("notForText").textContent = scope?.not_for || "";
}

function renderStatusBanner(runState, overview, inspector) {
  const host = document.getElementById("statusBanner");
  const phase = runState?.phase ?? "idle";
  const message = runState?.last_error || runState?.message || "Ready.";
  const chipClass = runState?.last_error
    ? "status-chip is-error"
    : runState?.is_running
      ? "status-chip is-running"
      : "status-chip";

  let chipText = "Idle";
  if (runState?.is_running) {
    chipText = "Running";
  } else if (inspector?.source_kind === "synthetic") {
    chipText = "Synthetic preview";
  } else if (inspector?.source_kind === "real") {
    chipText = "Real preview";
  } else if (overview?.instance_count) {
    chipText = `${overview.instance_count} demo instances ready`;
  }

  host.innerHTML = `
    <div>
      <strong>${escapeHtml(titleCase(phase))}</strong>
      <span>${escapeHtml(message)}</span>
    </div>
    <div class="${chipClass}">
      ${escapeHtml(chipText)}
    </div>
  `;
}

function renderInstanceInspector(inspector) {
  const payload = inspector || {};
  document.getElementById("inspectorTitle").textContent = payload.title || "No instance loaded";
  document.getElementById("inspectorDescription").textContent = payload.source_description || "";

  const badgeHost = document.getElementById("inspectorBadge");
  const badges = [];
  if (payload.mode_label) {
    badges.push(`<span class="scope-chip">${escapeHtml(payload.mode_label)}</span>`);
  }
  if (payload.source_badge) {
    const badgeClass = payload.source_kind === "synthetic" ? "scope-chip is-synthetic" : "scope-chip";
    badges.push(`<span class="${badgeClass}">${escapeHtml(payload.source_badge)}</span>`);
  }
  badgeHost.innerHTML = badges.join("");

  const summaryHost = document.getElementById("instanceSummary");
  const summaryItems = payload.summary_items || [];
  summaryHost.innerHTML = summaryItems.length
    ? summaryItems
        .map(
          (item) => `
            <article class="summary-card">
              <p class="label">${escapeHtml(item.label)}</p>
              <p class="value">${escapeHtml(formatCell(item.value))}</p>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">Load a real XML or generate a synthetic preview to inspect one instance.</div>`;

  const notesHost = document.getElementById("parserNotes");
  const parserNotes = payload.parser_notes || [];
  notesHost.innerHTML = parserNotes.length
    ? `
        <div class="notes-card">
          <p class="panel-kicker">Parser Notes</p>
          ${parserNotes
            .map((note) => {
              const badgeClass = note.severity === "warning" ? "note-badge is-warning" : "note-badge";
              return `
                <div class="note-row">
                  <span class="${badgeClass}">${escapeHtml(note.severity)}</span>
                  <div>
                    <strong>${escapeHtml(note.code)}</strong>
                    <p>${escapeHtml(note.message)}</p>
                  </div>
                </div>
              `;
            })
            .join("")}
        </div>
      `
    : `<div class="empty-state">No parser notes for the current instance.</div>`;

  const featureGroupsHost = document.getElementById("featureGroups");
  const featureGroups = payload.feature_groups || [];
  featureGroupsHost.innerHTML = featureGroups.length
    ? featureGroups
        .map(
          (group) => `
            <article class="feature-group-card">
              <div class="feature-group-head">
                <p class="panel-kicker">${escapeHtml(group.label)}</p>
              </div>
              <div class="feature-list">
                ${group.items
                  .map(
                    (item) => `
                      <div class="feature-row">
                        <span>${escapeHtml(labelize(item.name))}</span>
                        <strong>${escapeHtml(formatCell(item.value))}</strong>
                      </div>
                    `,
                  )
                  .join("")}
              </div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">Structural features will appear here after an instance is loaded.</div>`;
}

function renderStatsGrid(overview, training, evaluation) {
  const host = document.getElementById("statsGrid");
  const cards = [
    {
      label: "Synthetic demo instances",
      value: formatInt(overview.instance_count),
      subtext: `${formatInt(overview.feature_rows)} feature rows`,
    },
    {
      label: "Demo benchmark runs",
      value: formatInt(overview.benchmark_rows),
      subtext: `${formatInt(overview.solver_count)} solvers selected`,
    },
    {
      label: "Selector accuracy",
      value: formatPercent(training?.accuracy),
      subtext: `${formatInt(training?.num_train_rows)} train / ${formatInt(training?.num_test_rows)} test`,
    },
    {
      label: "Regret vs virtual best",
      value: formatFloat(evaluation?.regret_vs_virtual_best),
      subtext: `Improvement vs single best: ${formatFloat(evaluation?.improvement_vs_single_best)}`,
    },
  ];

  host.innerHTML = cards
    .map(
      (card) => `
        <article class="stat-card">
          <p class="label">${escapeHtml(card.label)}</p>
          <p class="value">${escapeHtml(card.value)}</p>
          <p class="subtext">${escapeHtml(card.subtext)}</p>
        </article>
      `,
    )
    .join("");
}

function renderTable(hostId, rows) {
  const host = document.getElementById(hostId);
  if (!rows || !rows.length) {
    host.innerHTML = `<div class="empty-state">No rows yet.</div>`;
    return;
  }

  const headers = Object.keys(rows[0]);
  const thead = headers.map((header) => `<th>${escapeHtml(labelize(header))}</th>`).join("");
  const body = rows
    .map((row) => {
      const cells = headers
        .map((header) => `<td>${escapeHtml(formatCell(row[header]))}</td>`)
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  host.innerHTML = `<table><thead><tr>${thead}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderBarList(hostId, rows, valueKey) {
  const host = document.getElementById(hostId);
  if (!rows || !rows.length) {
    host.innerHTML = `<div class="empty-state">No values yet.</div>`;
    return;
  }

  const maxValue = Math.max(...rows.map((row) => Number(row[valueKey] ?? 0)), 1);
  host.innerHTML = rows
    .map((row) => {
      const label = row.solver_name || row.feature || row.label || "Value";
      const value = Number(row[valueKey] ?? 0);
      const percent = Math.max(4, (value / maxValue) * 100);
      return `
        <div class="bar-item">
          <div class="bar-meta">
            <span>${escapeHtml(String(label))}</span>
            <span>${escapeHtml(formatCell(row[valueKey]))}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${percent}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderArtifacts(artifacts) {
  const host = document.getElementById("artifactList");
  const rows = Object.entries(artifacts || {});
  if (!rows.length) {
    host.innerHTML = `<div class="empty-state">Artifacts will appear after the first run.</div>`;
    return;
  }

  host.innerHTML = rows
    .map(([key, artifact]) => {
      const status = artifact.exists ? "Ready" : "Missing";
      const details = artifact.path_type === "directory"
        ? `${artifact.entry_count} files`
        : artifact.modified_at || "Not generated yet";
      return `
        <article class="artifact-card">
          <p class="label">${escapeHtml(labelize(key))}</p>
          <p class="value">${escapeHtml(status)}</p>
          <small>${escapeHtml(artifact.path || "")}</small>
          <p class="subtext">${escapeHtml(details)}</p>
        </article>
      `;
    })
    .join("");
}

function renderPreviewTabs(previews) {
  const host = document.getElementById("previewTabs");
  host.innerHTML = previewOrder
    .filter(([key]) => key in (previews || {}))
    .map(([key, label]) => {
      const activeClass = key === state.activePreviewKey ? "tab-button is-active" : "tab-button";
      return `<button class="${activeClass}" data-preview-key="${key}" type="button">${escapeHtml(label)}</button>`;
    })
    .join("");

  host.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activePreviewKey = button.dataset.previewKey;
      renderPreviewTabs(previews);
      renderPreviewTable();
    });
  });
}

function renderPreviewTable() {
  const rows = state.dashboard?.previews?.[state.activePreviewKey] || [];
  renderTable("previewHost", rows);
}

function renderTransientStatus(title, message, kind) {
  const host = document.getElementById("statusBanner");
  const chipClass = kind === "error" ? "status-chip is-error" : "status-chip";
  host.innerHTML = `
    <div>
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(message)}</span>
    </div>
    <div class="${chipClass}">
      ${escapeHtml(kind === "error" ? "Attention" : "Info")}
    </div>
  `;
}

function startPolling() {
  if (state.pollingTimer) {
    return;
  }
  state.pollingTimer = window.setInterval(() => {
    loadDashboardState().catch(() => null);
  }, 2500);
}

function stopPolling() {
  if (!state.pollingTimer) {
    return;
  }
  window.clearInterval(state.pollingTimer);
  state.pollingTimer = null;
}

function toggleBusy(isBusy) {
  [
    "loadRealButton",
    "previewButton",
    "runButton",
    "refreshButton",
    "realInstancePath",
    "syntheticDifficulty",
    "previewSeed",
    "instanceCount",
    "randomSeed",
    "timeLimit",
  ].forEach((id) => {
    const element = document.getElementById(id);
    if (element) {
      element.disabled = isBusy;
    }
  });
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      return String(value);
    }
    return value.toFixed(4);
  }
  return String(value);
}

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return `${(Number(value) * 100).toFixed(1)}%`;
}

function formatFloat(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return Number(value).toFixed(3);
}

function formatInt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }
  return Intl.NumberFormat().format(Number(value));
}

function titleCase(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function labelize(value) {
  return titleCase(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
