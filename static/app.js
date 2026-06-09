const state = {
  paperId: null,
  paperTitle: "Paper",
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

function setEmpty(id, text) {
  const element = $(id);
  element.classList.add("empty");
  element.innerHTML = text;
}

function setFilled(id, html) {
  const element = $(id);
  element.classList.remove("empty");
  element.innerHTML = html;
}

function revealElement(id) {
  requestAnimationFrame(() => {
    $(id).scrollIntoView({ behavior: "smooth", block: "center" });
  });
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
  } else {
    setStatus("0 papers");
    $("paperTitle").textContent = "Paper";
    $("paperText").textContent = "";
    state.paperTitle = "Paper";
  }
}

async function loadPaper(paperId) {
  setStatus("Loading");
  const paper = await api(`/api/papers/${encodeURIComponent(paperId)}`);
  state.paperId = paper.id;
  state.paperTitle = paper.title;
  $("paperTitle").textContent = paper.title;
  $("paperText").textContent = paper.text;
  setStatus(`${paper.text_length.toLocaleString()} chars`);
}

function renderGlossary(terms) {
  if (!terms.length) {
    setEmpty("glossaryOutput", "아직 없음");
    return;
  }
  setFilled(
    "glossaryOutput",
    terms.map((term) => `<span class="term">${escapeHtml(term.source)} → ${escapeHtml(term.target)}</span>`).join(""),
  );
}

async function summarize() {
  const button = $("summaryBtn");
  button.disabled = true;
  button.textContent = "요약 중";
  setEmpty("summaryOutput", "생성 중");
  try {
    const payload = {
      paper_id: state.paperId,
      session_id: state.sessionId,
      length_preset: $("lengthPreset").value,
      angle_preset: $("anglePreset").value,
    };
    const result = await api("/api/summarize", { method: "POST", body: JSON.stringify(payload) });
    setFilled(
      "summaryOutput",
      result.sentences
        .map(
          (sentence) => `
          <div class="sentence">
            <div>${escapeHtml(sentence.text)}</div>
            <span class="badge">${sentence.verification.label}</span>
          </div>
        `,
        )
        .join(""),
    );
    renderGlossary(result.glossary);
    revealElement("summaryOutput");
  } catch (error) {
    setFilled("summaryOutput", `<div class="sentence error">${escapeHtml(error.message)}</div>`);
    revealElement("summaryOutput");
  } finally {
    button.disabled = false;
    button.textContent = "요약 생성";
  }
}

async function translate() {
  const button = $("translateBtn");
  button.disabled = true;
  button.textContent = "번역 중";
  setEmpty("translationOutput", "번역 중");
  try {
    const payload = {
      paper_id: state.paperId,
      session_id: state.sessionId,
      selected_text: $("selectedText").value,
    };
    const result = await api("/api/translate", { method: "POST", body: JSON.stringify(payload) });
    setFilled(
      "translationOutput",
      result.units
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
        .join(""),
    );
    renderGlossary(result.glossary);
    revealElement("translationOutput");
  } catch (error) {
    setFilled("translationOutput", `<div class="unit error">${escapeHtml(error.message)}</div>`);
    revealElement("translationOutput");
  } finally {
    button.disabled = false;
    button.textContent = "선택 span 번역";
  }
}

async function openFullTranslation() {
  if (!state.paperId) {
    setFilled("translationOutput", `<div class="unit error">번역할 논문이 없습니다.</div>`);
    return;
  }

  const popup = window.open("", "_blank", "width=1180,height=840");
  if (!popup) {
    setFilled("translationOutput", `<div class="unit error">팝업이 차단되었습니다. 브라우저에서 팝업 허용 후 다시 시도하세요.</div>`);
    revealElement("translationOutput");
    return;
  }

  renderFullTranslationWindow(popup, state.paperTitle, "전체 원문을 불러오는 중입니다.", "");

  const button = $("fullTranslateBtn");
  button.disabled = true;
  button.textContent = "전체 번역 중";

  try {
    const paper = await api(`/api/papers/${encodeURIComponent(state.paperId)}/full`);
    renderFullTranslationWindow(popup, paper.title, "전체 번역을 생성하는 중입니다.", paper.text);
    const result = await api("/api/translate", {
      method: "POST",
      body: JSON.stringify({
        paper_id: state.paperId,
        session_id: state.sessionId,
        selected_text: paper.text,
      }),
    });
    renderFullTranslationWindow(popup, result.title, "", paper.text, result.units);
    renderGlossary(result.glossary);
  } catch (error) {
    renderFullTranslationWindow(popup, state.paperTitle, error.message, "");
  } finally {
    button.disabled = false;
    button.textContent = "전체 번역 보기";
  }
}

function renderFullTranslationWindow(target, title, status, sourceText, units = []) {
  const translatedHtml = units.length
    ? units
        .map(
          (unit) => `
            <article class="full-unit">
              <div class="anchor">${escapeHtml(unit.anchor)}</div>
              <p class="source">${escapeHtml(unit.source_text)}</p>
              <p class="translated">${escapeHtml(unit.translated_text)}</p>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state">${status || "번역 결과가 여기에 표시됩니다."}</div>`;

  target.document.open();
  target.document.write(`
    <!doctype html>
    <html lang="ko">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>${escapeHtml(title)} - 전체 번역</title>
        <style>
          :root {
            color-scheme: light;
            font-family: Inter, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", system-ui, sans-serif;
            color: #17201e;
            background: #f4f0e8;
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            background:
              radial-gradient(circle at 8% 0%, rgba(214, 95, 69, 0.12), transparent 32%),
              radial-gradient(circle at 90% 0%, rgba(15, 118, 110, 0.14), transparent 32%),
              #f4f0e8;
          }
          .full-shell {
            display: grid;
            gap: 18px;
            margin: 0 auto;
            max-width: 1320px;
            padding: 24px;
          }
          header {
            background: rgba(255, 253, 248, 0.88);
            border: 1px solid #ded8ca;
            border-radius: 20px;
            box-shadow: 0 18px 50px rgba(48, 39, 25, 0.1);
            padding: 18px 20px;
          }
          .eyebrow {
            color: #d65f45;
            display: inline-block;
            font-size: 11px;
            font-weight: 860;
            margin-bottom: 7px;
            text-transform: uppercase;
          }
          h1 {
            font-size: 24px;
            line-height: 1.25;
            margin: 0;
          }
          .status {
            color: #68726f;
            font-size: 13px;
            margin-top: 8px;
          }
          .split {
            display: grid;
            gap: 18px;
            grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          }
          section {
            background: rgba(255, 253, 248, 0.92);
            border: 1px solid #ded8ca;
            border-radius: 20px;
            box-shadow: 0 12px 34px rgba(48, 39, 25, 0.08);
            min-width: 0;
            overflow: hidden;
          }
          h2 {
            border-bottom: 1px solid #ded8ca;
            font-size: 15px;
            margin: 0;
            padding: 14px 16px;
          }
          pre, .translation-list {
            margin: 0;
            max-height: calc(100vh - 190px);
            overflow: auto;
            padding: 18px;
          }
          pre {
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
            font-size: 12px;
            line-height: 1.72;
            white-space: pre-wrap;
            word-break: break-word;
          }
          .translation-list {
            display: grid;
            gap: 12px;
          }
          .full-unit {
            background: #fffefa;
            border: 1px solid #e3dccf;
            border-radius: 16px;
            padding: 14px;
          }
          .anchor {
            background: #e1f1ee;
            border-radius: 999px;
            color: #0b5653;
            display: inline-flex;
            font-size: 11px;
            font-weight: 860;
            margin-bottom: 8px;
            padding: 4px 8px;
          }
          p {
            line-height: 1.65;
            margin: 0;
          }
          .source {
            color: #68726f;
            font-size: 12px;
            margin-bottom: 8px;
          }
          .translated {
            color: #17201e;
            font-size: 14px;
          }
          .empty-state {
            align-items: center;
            border: 1px dashed #cfc4b0;
            border-radius: 16px;
            color: #68726f;
            display: flex;
            font-size: 14px;
            font-weight: 760;
            justify-content: center;
            min-height: 160px;
            padding: 18px;
          }
          @media (max-width: 860px) {
            .full-shell { padding: 14px; }
            .split { grid-template-columns: 1fr; }
            pre, .translation-list { max-height: none; }
          }
        </style>
      </head>
      <body>
        <main class="full-shell">
          <header>
            <span class="eyebrow">Full Translation</span>
            <h1>${escapeHtml(title)}</h1>
            ${status ? `<div class="status">${status}</div>` : ""}
          </header>
          <div class="split">
            <section>
              <h2>원문</h2>
              <pre>${escapeHtml(sourceText || "")}</pre>
            </section>
            <section>
              <h2>번역</h2>
              <div class="translation-list">${translatedHtml}</div>
            </section>
          </div>
        </main>
      </body>
    </html>
  `);
  target.document.close();
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
$("fullTranslateBtn").addEventListener("click", openFullTranslation);
$("paperText").addEventListener("mouseup", () => {
  const selected = window.getSelection().toString().trim();
  if (selected) {
    $("selectedText").value = selected;
  }
});

loadPapers().catch((error) => {
  setStatus(error.message);
});
