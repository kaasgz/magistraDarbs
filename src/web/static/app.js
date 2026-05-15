const state = {
  presentation: null,
};

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("refreshButton").addEventListener("click", () => {
    loadDashboardState().catch(renderLoadError);
  });
  loadDashboardState().catch(renderLoadError);
});

async function loadDashboardState() {
  const response = await fetch("/api/state");
  const payload = await response.json();
  state.presentation = payload.presentation_dashboard || payload.thesis_visualization || null;
  renderPresentation();
}

function renderLoadError(error) {
  const host = document.getElementById("emptyState");
  host.hidden = false;
  host.textContent = error instanceof Error ? error.message : String(error);
}

function renderPresentation() {
  const presentation = state.presentation;
  const contentHost = document.getElementById("presentationContent");
  const emptyHost = document.getElementById("emptyState");

  if (!presentation?.available) {
    emptyHost.hidden = false;
    emptyHost.textContent = presentation?.empty_state || "Nav pieejamu datu rezultātu pārskatam.";
    contentHost.hidden = true;
    return;
  }

  emptyHost.hidden = true;
  contentHost.hidden = false;

  document.getElementById("pageTitle").textContent =
    presentation.header?.title || "Maģistra darba praktiskās daļas pārskats";
  document.getElementById("pageSubtitle").textContent = presentation.header?.subtitle || "";
  document.getElementById("pageAccentNote").textContent = presentation.header?.accent_note || "";

  renderSectionNav(presentation.navigation || []);
  renderOverviewSection(presentation.sections?.overview || {});
  renderWorkflowSection(presentation.sections?.workflow || {});
  renderResultsSection(presentation.sections?.results || {});
  renderSolverSection(presentation.sections?.solver || {});
  renderBestSolverSection(presentation.sections?.best_solver || {});
  renderFeatureSection(presentation.sections?.features || {});
  renderDatasetSection(presentation.sections?.datasets || {});
  renderMethodologySection(presentation.sections?.methodology || {});
  renderImplementationSection(presentation.sections?.implementation || {});
}

function renderSectionNav(items) {
  const host = document.getElementById("sectionNav");
  host.innerHTML = items
    .map(
      (item) => `
        <a class="nav-link" href="#section-${escapeHtml(item.id)}">
          ${escapeHtml(item.label)}
        </a>
      `,
    )
    .join("");
}

function renderOverviewSection(section) {
  setText("overviewTitle", section.title);
  setText("overviewIntro", section.intro);
  renderTakeaway("overviewTakeaway", section.takeaway);
  renderCards("overviewCards", section.cards || []);
  renderChipRow("overviewPortfolio", section.portfolio || []);
  renderHighlights("overviewHighlights", section.highlights || []);
  renderFigureGrid("overviewFigures", section.figures || []);
}

function renderWorkflowSection(section) {
  setText("workflowTitle", section.title);
  setText("workflowIntro", section.intro);
  renderTakeaway("workflowTakeaway", section.takeaway);
  setText("workflowTableTitle", section.table_title);
  setText("workflowTableNote", section.table_note);
  setText("workflowArtifactTableTitle", section.artifact_table_title);
  setText("workflowArtifactTableNote", section.artifact_table_note);
  setText("workflowCodeTableTitle", section.code_table_title);
  setText("workflowCodeTableNote", section.code_table_note);
  renderCards("workflowCards", section.cards || []);
  renderHighlights("workflowHighlights", section.highlights || []);
  renderTable("workflowTable", section.table_rows || []);
  renderTable("workflowArtifactTable", section.artifact_rows || []);
  renderTable("workflowCodeTable", section.code_rows || []);
}

function renderResultsSection(section) {
  setText("resultsTitle", section.title);
  setText("resultsIntro", section.intro);
  renderTakeaway("resultsTakeaway", section.takeaway);
  renderCards("resultsCards", section.cards || []);
  renderFigureGrid("resultsFigures", section.figures || []);
}

function renderSolverSection(section) {
  setText("solverTitle", section.title);
  setText("solverIntro", section.intro);
  renderTakeaway("solverTakeaway", section.takeaway);
  setText("solverTableTitle", section.table_title);
  setText("solverTableNote", section.table_note);
  renderFigureGrid("solverFigures", section.figures || []);
  renderTable("solverTable", section.table_rows || []);
}

function renderBestSolverSection(section) {
  setText("bestSolverTitle", section.title);
  setText("bestSolverIntro", section.intro);
  renderTakeaway("bestSolverTakeaway", section.takeaway);
  setText("bestSolverTableTitle", section.table_title);
  setText("bestSolverTableNote", section.table_note);
  renderCards("bestSolverCards", section.cards || []);
  renderHighlights("bestSolverHighlights", section.highlights || []);
  renderFigureGrid("bestSolverFigures", section.figures || []);
  renderTable("bestSolverTable", section.table_rows || []);
}

function renderFeatureSection(section) {
  setText("featuresTitle", section.title);
  setText("featuresIntro", section.intro);
  renderTakeaway("featuresTakeaway", section.takeaway);
  setText("featuresHighlight", section.highlight);
  setText("featureTableTitle", section.table_title);
  setText("featureSecondaryTableTitle", section.secondary_table_title);
  renderFigureGrid("featureFigures", section.figures || []);
  renderTable("featureTable", section.table_rows || []);
  renderTable("featureSecondaryTable", section.secondary_table_rows || []);
}

function renderDatasetSection(section) {
  setText("datasetsTitle", section.title);
  setText("datasetsIntro", section.intro);
  renderTakeaway("datasetsTakeaway", section.takeaway);
  setText("datasetTableTitle", section.table_title);
  setText("datasetTableNote", section.table_note);
  renderFigureGrid("datasetFigures", section.figures || []);
  renderTable("datasetTable", section.table_rows || []);
}

function renderMethodologySection(section) {
  setText("methodologyTitle", section.title);
  setText("methodologyIntro", section.intro);
  renderTakeaway("methodologyTakeaway", section.takeaway);
  setText("methodologyTableTitle", section.table_title);
  setText("methodologyTableNote", section.table_note);
  renderCards("methodologyCards", section.cards || []);
  renderHighlights("methodologyHighlights", section.highlights || []);
  renderFigureGrid("methodologyFigures", section.figures || []);
  renderTable("methodologyTable", section.table_rows || []);
}

function renderImplementationSection(section) {
  setText("implementationTitle", section.title);
  setText("implementationIntro", section.intro);
  renderTakeaway("implementationTakeaway", section.takeaway);
  setText("implementationTableTitle", section.table_title);
  setText("implementationTableNote", section.table_note);
  setText("implementationArtifactTableTitle", section.artifact_table_title);
  setText("implementationArtifactTableNote", section.artifact_table_note);
  renderCards("implementationCards", section.cards || []);
  renderTable("implementationTable", section.table_rows || []);
  renderTable("implementationArtifactTable", section.artifact_rows || []);
}

function renderCards(hostId, cards) {
  const host = document.getElementById(hostId);
  host.innerHTML = cards
    .map(
      (card) => `
        <article class="summary-card">
          <p class="label">${escapeHtml(card.label || "")}</p>
          <p class="value">${escapeHtml(formatCell(card.value))}</p>
          <p class="card-description">${escapeHtml(card.description || "")}</p>
        </article>
      `,
    )
    .join("");
}

function renderChipRow(hostId, items) {
  const host = document.getElementById(hostId);
  const normalized = items.filter(Boolean);
  host.innerHTML = normalized.map((item) => `<span class="chip">${escapeHtml(item)}</span>`).join("");
  const block = host.closest(".chip-block");
  if (block) {
    block.hidden = normalized.length === 0;
  }
}

function renderHighlights(hostId, items) {
  const host = document.getElementById(hostId);
  const normalized = items.filter(Boolean);
  host.hidden = normalized.length === 0;
  host.innerHTML = normalized
    .map((item) => `<div class="highlight-item">${escapeHtml(item)}</div>`)
    .join("");
}

function renderFigureGrid(hostId, figures) {
  const host = document.getElementById(hostId);
  const visibleFigures = figures.filter((figure) => figure.exists && figure.url);
  host.hidden = visibleFigures.length === 0;
  host.innerHTML = visibleFigures
    .map(
      (figure) => `
        <article class="figure-card">
          <img src="${escapeHtml(figure.url)}" alt="${escapeHtml(figure.title || "")}" />
          <h3 class="figure-title">${escapeHtml(figure.title || "")}</h3>
          <p class="chart-description">${escapeHtml(figure.description || "")}</p>
          <p class="chart-meaning">${escapeHtml(figure.meaning || "")}</p>
          <a class="figure-link" href="${escapeHtml(figure.url)}" target="_blank" rel="noopener">Atvērt attēlu pilnā izmērā</a>
        </article>
      `,
    )
    .join("");
}

function renderTakeaway(id, value) {
  const element = document.getElementById(id);
  if (!element) {
    return;
  }
  const text = value || "";
  element.hidden = text.length === 0;
  element.innerHTML = text ? `<strong>${escapeHtml(text)}</strong>` : "";
}

function renderTable(hostId, rows) {
  const host = document.getElementById(hostId);
  if (!host) {
    return;
  }
  if (!rows.length) {
    host.innerHTML = `<div class="empty-state">Tabulas dati nav pieejami.</div>`;
    return;
  }

  const columns = Object.keys(rows[0]);
  const header = columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
  const body = rows
    .map(
      (row) => `
        <tr>
          ${columns.map((column) => `<td>${escapeHtml(formatCell(row[column]))}</td>`).join("")}
        </tr>
      `,
    )
    .join("");

  host.innerHTML = `
    <table>
      <thead>
        <tr>${header}</tr>
      </thead>
      <tbody>${body}</tbody>
    </table>
  `;
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = value || "";
  }
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      return String(value);
    }
    return value.toFixed(4).replace(/0+$/, "").replace(/\.$/, "").replace(".", ",");
  }
  if (typeof value === "string" && /^-?\d+\.\d+$/.test(value.trim())) {
    return Number(value).toFixed(4).replace(/0+$/, "").replace(/\.$/, "").replace(".", ",");
  }
  return String(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
