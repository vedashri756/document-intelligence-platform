const API_BASE = "/api/v1"; // matches the spec's required endpoint prefix

const form = document.getElementById("upload-form");
const statusDiv = document.getElementById("upload-status");
const tableBody = document.querySelector("#doc-table tbody");
const detailCard = document.getElementById("detail-card");
const detailContent = document.getElementById("detail-content");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("process-btn");
  const file = document.getElementById("file").files[0];
  const documentType = document.getElementById("document_type").value;
  if (!file) return;

  btn.disabled = true;
  statusDiv.textContent = "Processing... this can take a few seconds (OCR + LLM extraction).";
  statusDiv.style.color = "#667";

  const fd = new FormData();
  fd.append("document_type", documentType);
  fd.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/documents/process`, { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      statusDiv.textContent = `Error: ${data.message || "processing failed"}`;
      statusDiv.style.color = "var(--fail)";
    } else {
      statusDiv.textContent = `Processed "${data.document_name}" successfully.`;
      statusDiv.style.color = "var(--pass)";
      loadDocuments();
      renderDetail(data);
    }
  } catch (err) {
    statusDiv.textContent = `Network error: ${err.message}`;
    statusDiv.style.color = "var(--fail)";
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("refresh-btn").addEventListener("click", loadDocuments);

async function loadDocuments() {
  const res = await fetch(`${API_BASE}/documents`);
  const docs = await res.json();
  tableBody.innerHTML = "";
  docs.forEach((d) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${d.document_name}</td>
      <td>${d.document_type}</td>
      <td class="status-${d.status}">${d.status}</td>
      <td>${new Date(d.processed_at).toLocaleString()}</td>
    `;
    tr.addEventListener("click", async () => {
      const r = await fetch(`${API_BASE}/documents/${encodeURIComponent(d.document_name)}`);
      const full = await r.json();
      renderDetail(full);
    });
    tableBody.appendChild(tr);
  });
}

function renderDetail(doc) {
  detailCard.style.display = "block";
  const fields = doc.extracted_data?.fields || [];
  const tables = doc.extracted_data?.tables || [];
  const validations = doc.validations || [];

  const fieldsHtml = fields.map((f) => `
    <div class="field-row ${f.value === null ? "missing" : ""}">
      <span>${f.name}${f.page ? ` (p.${f.page})` : ""}</span>
      <span>${f.value === null ? "MISSING" : f.value}</span>
    </div>
  `).join("");

  const tablesHtml = tables.map((t) => `
    <div class="section-title">${t.table_name}</div>
    <table>
      <thead><tr>${t.columns.map((c) => `<th>${c}</th>`).join("")}</tr></thead>
      <tbody>
        ${t.rows.map((r) => `<tr>${r.map((c) => `<td>${c ?? ""}</td>`).join("")}</tr>`).join("")}
      </tbody>
    </table>
  `).join("");

  const validationsHtml = validations.map((v) => `
    <div class="validation-item ${v.status}">
      <strong>${v.check_name}</strong> — <span class="status-${v.status === "PASS" ? "pass" : v.status === "FAIL" ? "fail" : "na"}">${v.status}</span>
      <div style="font-size:12px;color:#666;">formula: ${v.formula}</div>
      ${v.calculated_value !== null && v.calculated_value !== undefined ? `<div style="font-size:12px;">calculated: ${v.calculated_value} | reported: ${v.reported_value} | variance: ${v.variance}</div>` : ""}
      ${v.note ? `<div style="font-size:12px;color:#888;">${v.note}</div>` : ""}
    </div>
  `).join("");

  detailContent.innerHTML = `
    <p><strong>${doc.document_name}</strong> — ${doc.document_type} — <span class="status-${doc.status}">${doc.status}</span></p>
    <div class="section-title">Extracted fields</div>
    ${fieldsHtml || "<p>No fields extracted.</p>"}
    ${tablesHtml}
    <div class="section-title">Financial validations</div>
    ${validationsHtml || "<p>No validations applicable.</p>"}
    <div class="section-title">Raw JSON</div>
    <pre class="json-view">${JSON.stringify(doc, null, 2)}</pre>
  `;
  detailCard.scrollIntoView({ behavior: "smooth" });
}

loadDocuments();
