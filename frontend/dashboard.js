let sentimentChart, categoryChart, confidenceChart, trendChart, themeChart, feedbackModal;
let clientContext;

function detectClientContext() {
  const ua = navigator.userAgent;

  let browser = "Unknown";
  if (/Edg\//.test(ua)) browser = "Edge";
  else if (/OPR\//.test(ua)) browser = "Opera";
  else if (/Chrome\//.test(ua)) browser = "Chrome";
  else if (/Firefox\//.test(ua)) browser = "Firefox";
  else if (/Safari\//.test(ua)) browser = "Safari";

  let platform = "Unknown";
  if (/Windows/.test(ua)) platform = "Windows";
  else if (/Android/.test(ua)) platform = "Android";
  else if (/iPhone|iPad|iPod/.test(ua)) platform = "iOS";
  else if (/Mac OS X/.test(ua)) platform = "macOS";
  else if (/Linux/.test(ua)) platform = "Linux";

  const device = /Mobi|Android/i.test(ua) ? "Mobile" : "Desktop";

  return { device, browser, platform };
}

// Fields with no genuine client-side signal (no per-product config, no
// business-region API) - synthetic sample values, freshly randomized per
// submission rather than left permanently null.
const PRODUCTS = ["Invoicing", "Reporting", "Payments", "Onboarding", "Analytics"];
const MODULES = ["Uploads", "Checkout", "Dashboard", "Settings", "Notifications"];
const VERSIONS = ["1.4.2", "2.0.0", "2.3.1", "3.1.0", "4.0.0-beta"];
const REGIONS = ["US-East", "US-West", "EU-West", "APAC", "LATAM"];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateSyntheticMetadata() {
  return { product: pick(PRODUCTS), module: pick(MODULES), version: pick(VERSIONS), region: pick(REGIONS) };
}

// user_id is derived from whatever identity the person actually typed
// (email preferred as the more stable identifier, name as a fallback)
// rather than randomized independently of it.
function deriveUserId(name, email) {
  const source = email || name;
  if (!source) return null;
  return source
    .split("@")[0]
    .toLowerCase()
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "");
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${url} (${res.status})`);
  }
  return res.json();
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

function upsertChart(existing, canvas, config) {
  if (existing) {
    existing.destroy();
  }
  return new Chart(canvas, config);
}

function renderKPIs(analytics) {
  const cards = [
    ["Total Feedback", analytics.total_feedback],
    ["Positive %", `${analytics.positive_pct}%`],
    ["Neutral %", `${analytics.neutral_pct}%`],
    ["Negative %", `${analytics.negative_pct}%`],
    ["Incidents", analytics.incidents],
    ["Service Requests", analytics.service_requests],
    ["General Feedback", analytics.general_feedback],
    ["Avg Confidence", analytics.average_confidence !== null ? `${analytics.average_confidence}%` : "-"],
  ];

  document.getElementById("kpi-cards").innerHTML = cards
    .map(
      ([label, value]) => `
        <div class="col-6 col-md-3">
          <div class="card text-center p-3 h-100">
            <div class="fs-4 fw-bold">${value}</div>
            <div class="text-muted small">${label}</div>
          </div>
        </div>
      `
    )
    .join("");
}

function renderSentimentChart(analytics) {
  const canvas = document.getElementById("sentimentChart");
  sentimentChart = upsertChart(sentimentChart, canvas, {
    type: "pie",
    data: {
      labels: analytics.sentiment_breakdown.map((s) => s.sentiment),
      datasets: [{ data: analytics.sentiment_breakdown.map((s) => s.count) }],
    },
  });
}

function renderCategoryChart(analytics) {
  const canvas = document.getElementById("categoryChart");
  categoryChart = upsertChart(categoryChart, canvas, {
    type: "bar",
    data: {
      labels: analytics.category_breakdown.map((c) => c.main_category),
      datasets: [{ label: "Feedback Count", data: analytics.category_breakdown.map((c) => c.count) }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function renderConfidenceChart(analytics) {
  const canvas = document.getElementById("confidenceChart");
  confidenceChart = upsertChart(confidenceChart, canvas, {
    type: "bar",
    data: {
      labels: analytics.confidence_distribution.map((b) => b.range),
      datasets: [{ label: "Feedback Count", data: analytics.confidence_distribution.map((b) => b.count) }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

function renderTrendChart(analytics) {
  const canvas = document.getElementById("trendChart");
  trendChart = upsertChart(trendChart, canvas, {
    type: "line",
    data: {
      labels: analytics.weekly_trend.map((w) => w.week_start),
      datasets: [
        { label: "Feedback per Week", data: analytics.weekly_trend.map((w) => w.count), tension: 0.3 },
      ],
    },
    options: { scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });
}

function renderThemeChart(themes) {
  const canvas = document.getElementById("themeChart");
  themeChart = upsertChart(themeChart, canvas, {
    type: "bar",
    data: {
      labels: themes.map((t) => t.name),
      datasets: [{ label: "Occurrences", data: themes.map((t) => t.count) }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
}

async function loadAnalytics() {
  const analytics = await fetchJSON("/analytics");
  renderKPIs(analytics);
  renderSentimentChart(analytics);
  renderCategoryChart(analytics);
  renderConfidenceChart(analytics);
  renderTrendChart(analytics);
}

async function loadThemes() {
  const themes = await fetchJSON("/themes?limit=10");
  renderThemeChart(themes);
}

function buildFeedbackFilterParams() {
  const params = new URLSearchParams();
  const category = document.getElementById("filter-category").value;
  const sentiment = document.getElementById("filter-sentiment").value;
  const search = document.getElementById("search-input").value.trim();
  if (category) params.set("main_category", category);
  if (sentiment) params.set("sentiment", sentiment);
  if (search) params.set("search", search);
  return params;
}

function buildFeedbackQuery() {
  const params = buildFeedbackFilterParams();
  params.set("limit", "50");
  return params.toString();
}

function renderFeedbackTable(items) {
  const tbody = document.getElementById("feedback-table-body");

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted py-4">No feedback found.</td></tr>`;
    return;
  }

  tbody.innerHTML = items
    .map(
      (f) => `
        <tr data-id="${f.id}" class="feedback-row">
          <td>${f.id}</td>
          <td>${escapeHtml(f.raw_text).slice(0, 80)}</td>
          <td>${f.source ?? "-"}</td>
          <td>${escapeHtml(f.product) || "-"}</td>
          <td>${f.main_category ?? "-"}</td>
          <td>${f.sentiment ?? "-"}</td>
          <td>${f.priority ?? "-"}</td>
          <td>${f.confidence ?? "-"}</td>
          <td>${new Date(f.created_at).toLocaleString()}</td>
        </tr>
      `
    )
    .join("");

  tbody.querySelectorAll("tr[data-id]").forEach((row) => {
    row.addEventListener("click", () => showFeedbackDetail(row.dataset.id));
  });
}

async function loadFeedbackTable() {
  const query = buildFeedbackQuery();
  const items = await fetchJSON(`/feedback?${query}`);
  renderFeedbackTable(items);
}

async function showFeedbackDetail(id) {
  const f = await fetchJSON(`/feedback/${id}`);
  document.getElementById("feedback-modal-body").innerHTML = `
    <p><strong>Text:</strong> ${escapeHtml(f.raw_text)}</p>
    <p><strong>Category:</strong> ${f.main_category ?? "-"} / ${f.sub_category ?? "-"}</p>
    <p><strong>Sentiment:</strong> ${f.sentiment ?? "-"}</p>
    <p><strong>Priority:</strong> ${f.priority ?? "-"}</p>
    <p><strong>Confidence:</strong> ${f.confidence ?? "-"}</p>
    <p><strong>Summary:</strong> ${escapeHtml(f.summary)}</p>
    <p><strong>Themes:</strong> ${f.themes.length ? f.themes.map(escapeHtml).join(", ") : "-"}</p>
    <hr>
    <p><strong>Source:</strong> ${f.source ?? "-"}</p>
    <p><strong>Product / Module / Version:</strong> ${escapeHtml(f.product) || "-"} / ${escapeHtml(f.module) || "-"} / ${escapeHtml(f.version) || "-"}</p>
    <p><strong>User ID:</strong> ${escapeHtml(f.user_id) || "-"}</p>
    <p><strong>Name:</strong> ${escapeHtml(f.name) || "-"}</p>
    <p><strong>Email:</strong> ${escapeHtml(f.email) || "-"}</p>
    <p><strong>Region:</strong> ${escapeHtml(f.region) || "-"}</p>
    <p><strong>Device / Browser / Platform:</strong> ${escapeHtml(f.device) || "-"} / ${escapeHtml(f.browser) || "-"} / ${escapeHtml(f.platform) || "-"}</p>
    <p class="text-muted small mb-0">Created: ${new Date(f.created_at).toLocaleString()}</p>
    ${renderAttachmentsList(f.attachments)}
  `;
  feedbackModal.show();
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function renderAttachmentsList(attachments) {
  if (!attachments || !attachments.length) {
    return "";
  }
  const items = attachments
    .map(
      (a) => `
        <li>
          <a href="/attachments/${a.id}/download" target="_blank" rel="noopener">${escapeHtml(a.filename)}</a>
          <span class="text-muted small">(${formatFileSize(a.size_bytes)})</span>
        </li>
      `
    )
    .join("");
  return `<hr><p class="mb-1"><strong>Attachments:</strong></p><ul class="mb-0">${items}</ul>`;
}

async function refreshAll() {
  await Promise.all([loadAnalytics(), loadThemes(), loadFeedbackTable()]);
}

function renderBulletList(label, items) {
  if (!items || !items.length) return "";
  const lis = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  return `<p class="mb-1"><strong>${label}:</strong></p><ul>${lis}</ul>`;
}

function renderExcerptList(label, excerpts) {
  if (!excerpts || !excerpts.length) return "";
  const lis = excerpts
    .map((e) => {
      const tags = [e.main_category, e.sentiment, e.priority].filter(Boolean).join(" / ");
      return `<li>${tags ? `<span class="text-muted small">[${tags}]</span> ` : ""}${escapeHtml(e.raw_text)}</li>`;
    })
    .join("");
  return `<p class="mb-1"><strong>${label}:</strong></p><ul>${lis}</ul>`;
}

async function loadWeeklyReport() {
  const btn = document.getElementById("weekly-report-btn");
  const statusEl = document.getElementById("weekly-report-status");
  const bodyEl = document.getElementById("weekly-report-body");

  btn.disabled = true;
  btn.textContent = "Generating...";
  statusEl.textContent = "";
  bodyEl.innerHTML = "";

  try {
    const report = await fetchJSON("/reports/weekly");
    const start = new Date(report.period_start).toLocaleDateString();
    const end = new Date(report.period_end).toLocaleDateString();
    bodyEl.innerHTML = `
      <p class="text-muted small">Period: ${start} - ${end}</p>
      <p class="text-muted small">
        ${report.metrics.total_feedback} feedback items ·
        ${report.metrics.positive_pct}% positive ·
        ${report.metrics.neutral_pct}% neutral ·
        ${report.metrics.negative_pct}% negative
      </p>
      <p>${escapeHtml(report.executive_summary)}</p>
      ${renderBulletList("Key Wins", report.key_wins)}
      ${renderBulletList("Key Concerns", report.key_concerns)}
      ${renderBulletList("Recommended Actions", report.recommended_actions)}
      ${renderExcerptList("Top Concerns", report.top_concerns)}
      ${renderExcerptList("Positive Highlights", report.positive_highlights)}
    `;
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Report";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  feedbackModal = new bootstrap.Modal(document.getElementById("feedback-modal"));

  clientContext = detectClientContext();
  document.getElementById("detected-context").textContent =
    `Detected: ${clientContext.device} · ${clientContext.browser} · ${clientContext.platform}`;

  document.getElementById("refresh-btn").addEventListener("click", refreshAll);
  document.getElementById("filter-category").addEventListener("change", loadFeedbackTable);
  document.getElementById("filter-sentiment").addEventListener("change", loadFeedbackTable);
  document.getElementById("search-input").addEventListener("input", debounce(loadFeedbackTable, 300));

  document.getElementById("export-csv-btn").addEventListener("click", () => {
    window.location.href = `/feedback/export/csv?${buildFeedbackFilterParams().toString()}`;
  });
  document.getElementById("export-pdf-btn").addEventListener("click", () => {
    window.location.href = `/feedback/export/pdf?${buildFeedbackFilterParams().toString()}`;
  });

  // Not part of refreshAll() - this triggers a real LLM call, so it only
  // runs on an explicit click, never on page load or routine refresh.
  document.getElementById("weekly-report-btn").addEventListener("click", loadWeeklyReport);

  document.getElementById("feedback-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const textInput = document.getElementById("feedback-text");
    const statusEl = document.getElementById("feedback-form-status");
    const text = textInput.value.trim();
    if (!text) return;

    const submitBtn = event.target.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Classifying...";
    statusEl.textContent = "";

    const name = document.getElementById("feedback-name").value.trim();
    const email = document.getElementById("feedback-email").value.trim();

    const payload = {
      raw_text: text,
      source: "Web Form",
      ...clientContext,
      ...generateSyntheticMetadata(),
    };
    if (name) payload.name = name;
    if (email) payload.email = email;
    const userId = deriveUserId(name, email);
    if (userId) payload.user_id = userId;

    const attachmentsInput = document.getElementById("feedback-attachments");
    const attachmentFiles = attachmentsInput.files;

    try {
      const res = await fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Submit failed (${res.status})`);
      const created = await res.json();

      if (attachmentFiles.length) {
        const formData = new FormData();
        for (const file of attachmentFiles) {
          formData.append("files", file);
        }
        const attachRes = await fetch(`/feedback/${created.id}/attachments`, {
          method: "POST",
          body: formData,
        });
        if (!attachRes.ok) throw new Error(`Attachment upload failed (${attachRes.status})`);
      }

      event.target.reset();
      statusEl.textContent = "Feedback submitted and classified.";
      await refreshAll();
    } catch (err) {
      statusEl.textContent = `Error: ${err.message}`;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Submit";
    }
  });

  document.getElementById("bulk-upload-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const fileInput = document.getElementById("bulk-upload-file");
    const statusEl = document.getElementById("bulk-upload-status");
    if (!fileInput.files.length) return;

    const submitBtn = event.target.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Uploading...";
    statusEl.textContent = "";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
      const res = await fetch("/bulk-upload/file", { method: "POST", body: formData });
      const body = await res.json();
      if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
      event.target.reset();
      statusEl.textContent = `Uploaded and classified ${body.length} feedback item(s).`;
      await refreshAll();
    } catch (err) {
      statusEl.textContent = `Error: ${err.message}`;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Upload";
    }
  });

  refreshAll();
});
