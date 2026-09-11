const API_BASE = "/api/v1";

function statusPillClass(status) {
  const s = (status || "").toLowerCase();
  if (s === "pass") return "pill pass";
  if (s === "fail" || s === "failed") return "pill fail";
  return "pill na";
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

/* ---------------- Upload page ---------------- */
function initUploadForm() {
  const form = document.getElementById("upload-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const statusLine = document.getElementById("status-line");
    const submitBtn = document.getElementById("submit-btn");
    const resultCard = document.getElementById("result-card");

    const fileInput = document.getElementById("file");
    const docType = document.getElementById("document_type").value;

    if (!fileInput.files.length) {
      statusLine.textContent = "Choose a file first.";
      statusLine.classList.add("error");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("document_type", docType);

    submitBtn.disabled = true;
    statusLine.classList.remove("error");
    statusLine.textContent = "Processing… this can take a few seconds for OCR/extraction.";
    resultCard.style.display = "none";

    try {
      const res = await fetch(`${API_BASE}/documents/process`, { method: "POST", body: formData });
      const data = await res.json();

      if (!res.ok) {
        const message = data?.error?.message || "Processing failed.";
        statusLine.textContent = `Error: ${message}`;
        statusLine.classList.add("error");
        return;
      }

      statusLine.textContent = `Done. Status: ${data.processing_status}.`;
      resultCard.style.display = "block";
      document.getElementById("result-summary").textContent =
        `${data.document_name} (${data.document_type}) processed with status ${data.processing_status}.`;
      const link = document.getElementById("result-link");
      link.href = `/document/${encodeURIComponent(data.document_name)}`;
    } catch (err) {
      statusLine.textContent = "Network error while contacting the API.";
      statusLine.classList.add("error");
    } finally {
      submitBtn.disabled = false;
    }
  });
}

/* ---------------- Dashboard page ---------------- */
async function initDashboard() {
  const tbody = document.getElementById("doc-table-body");
  if (!tbody) return;

  try {
    const res = await fetch(`${API_BASE}/documents`);
    const docs = await res.json();

    if (!docs.length) {
      document.getElementById("empty-state").style.display = "block";
      return;
    }

    docs.forEach((doc) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(doc.document_name)}</td>
        <td>${escapeHtml(doc.document_type)}</td>
        <td><span class="${statusPillClass(doc.processing_status)}">${escapeHtml(doc.processing_status)}</span></td>
        <td>${new Date(doc.processed_at).toLocaleString()}</td>
      `;
      tr.addEventListener("click", () => {
        window.location.href = `/document/${encodeURIComponent(doc.document_name)}`;
      });
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4">Could not load documents.</td></tr>`;
  }
}

/* ---------------- Document result page ---------------- */
async function initResultPage() {
  const titleEl = document.getElementById("doc-title");
  if (!titleEl) return;

  const documentName = window.DOCUMENT_NAME;
  try {
    const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(documentName)}`);
    const data = await res.json();

    if (!res.ok) {
      titleEl.textContent = "Document not found";
      document.getElementById("doc-subtitle").textContent = data?.error?.message || "";
      return;
    }

    titleEl.textContent = data.document_name;
    document.getElementById("doc-subtitle").innerHTML =
      `${escapeHtml(data.document_type)} &middot; <span class="${statusPillClass(data.processing_status)}">${escapeHtml(data.processing_status)}</span>` +
      (data.file_validation ? ` &middot; ${data.file_validation.page_count} page(s)` : "");

    // Extracted fields
    const dl = document.getElementById("extracted-fields");
    const lineItems = data.extracted_data?.line_items;
    Object.entries(data.extracted_data || {}).forEach(([key, val]) => {
      if (key === "line_items") return;
      const dt = document.createElement("dt");
      dt.textContent = key;
      const dd = document.createElement("dd");
      const value = val && typeof val === "object" ? val.value : val;
      if (value === null || value === undefined) {
        dd.className = "missing";
        dd.textContent = "Not found in document";
      } else {
        dd.textContent = value;
      }
      if (val && typeof val === "object" && val.source_text) {
        const ev = document.createElement("div");
        ev.className = "evidence";
        ev.textContent = `“${val.source_text}”${val.page_number ? " — p." + val.page_number : ""}`;
        dd.appendChild(document.createElement("br"));
        dd.appendChild(ev);
      }
      dl.appendChild(dt);
      dl.appendChild(dd);
    });

    // Line items table
    if (Array.isArray(lineItems) && lineItems.length) {
      document.getElementById("line-items-card").style.display = "block";
      const columns = Object.keys(lineItems[0]);
      document.getElementById("line-items-head").innerHTML =
        columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("");
      document.getElementById("line-items-body").innerHTML = lineItems
        .map((row) => `<tr>${columns.map((c) => `<td>${escapeHtml(row[c] ?? "")}</td>`).join("")}</tr>`)
        .join("");
    }

    // Validation checks
    const checksBody = document.getElementById("checks-body");
    (data.validation?.checks || []).forEach((check) => {
      const tr = document.createElement("tr");
      if (check.status === "FAIL") tr.querySelectorAll?.length; // no-op, class added below
      tr.innerHTML = `
        <td>${escapeHtml(check.name)}</td>
        <td><code>${escapeHtml(check.formula)}</code></td>
        <td>${check.calculated_value ?? "—"}</td>
        <td>${check.reported_value ?? "—"}</td>
        <td>${check.variance ?? "—"}</td>
        <td><span class="${statusPillClass(check.status)}">${escapeHtml(check.status)}</span></td>
      `;
      if (check.status === "FAIL") tr.classList.add("fail-row");
      checksBody.appendChild(tr);
    });

    document.getElementById("raw-json").textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    titleEl.textContent = "Could not load document";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initUploadForm();
  initDashboard();
  initResultPage();
});
