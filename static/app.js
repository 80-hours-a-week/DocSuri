const state = {
  paperId: null,
  sessionId: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
};

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || response.statusText);
  }
  return response.json();
}

function setStatus(text) {
  $("status").textContent = text;
}

async function loadPapers() {
  const papers = await api("/api/papers");
  const select = $("paperSelect");
  select.innerHTML = "";
  for (const paper of papers) {
    const option = document.createElement("option");
    option.value = paper.id;
    option.textContent = paper.title;
    select.append(option);
  }
  state.paperId = papers[0]?.id;
  if (state.paperId) {
    await loadPaper(state.paperId);
  }
}

async function loadPaper(paperId) {
  setStatus("Loading");
  const paper = await api(`/api/papers/${encodeURIComponent(paperId)}`);
  state.paperId = paper.id;
  $("paperTitle").textContent = paper.title;
  $("paperText").textContent = paper.text;
  setStatus(`${paper.text_length.toLocaleString()} chars`);
}

function renderGlossary(terms) {
  $("glossaryOutput").innerHTML = terms
    .map((term) => `<span class="term">${escapeHtml(term.source)} → ${escapeHtml(term.target)}</span>`)
    .join("");
}

async function summarize() {
  const button = $("summaryBtn");
  button.disabled = true;
  button.textContent = "요약 중";
  try {
    const payload = {
      paper_id: state.paperId,
      session_id: state.sessionId,
      length_preset: $("lengthPreset").value,
      angle_preset: $("anglePreset").value,
    };
    const result = await api("/api/summarize", { method: "POST", body: JSON.stringify(payload) });
    $("summaryOutput").innerHTML = result.sentences
      .map(
        (sentence) => `
          <div class="sentence">
            <div>${escapeHtml(sentence.text)}</div>
            <span class="badge">${sentence.verification.label}</span>
          </div>
        `,
      )
      .join("");
    renderGlossary(result.glossary);
  } catch (error) {
    $("summaryOutput").innerHTML = `<div class="sentence">${escapeHtml(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = "요약 생성";
  }
}

async function translate() {
  const button = $("translateBtn");
  button.disabled = true;
  button.textContent = "번역 중";
  try {
    const payload = {
      paper_id: state.paperId,
      session_id: state.sessionId,
      selected_text: $("selectedText").value,
    };
    const result = await api("/api/translate", { method: "POST", body: JSON.stringify(payload) });
    $("translationOutput").innerHTML = result.units
      .map(
        (unit) => `
          <div class="unit">
            <strong>${escapeHtml(unit.anchor)}</strong>
            <p>${escapeHtml(unit.source_text)}</p>
            <div>${escapeHtml(unit.translated_text)}</div>
            <span class="badge">${unit.verification.label}</span>
          </div>
        `,
      )
      .join("");
    renderGlossary(result.glossary);
  } catch (error) {
    $("translationOutput").innerHTML = `<div class="unit">${escapeHtml(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = "선택 span 번역";
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

$("paperSelect").addEventListener("change", (event) => loadPaper(event.target.value));
$("summaryBtn").addEventListener("click", summarize);
$("translateBtn").addEventListener("click", translate);
$("paperText").addEventListener("mouseup", () => {
  const selected = window.getSelection().toString().trim();
  if (selected) {
    $("selectedText").value = selected;
  }
});

loadPapers().catch((error) => {
  setStatus(error.message);
});
