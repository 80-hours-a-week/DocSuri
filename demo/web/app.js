/* ============================================================
   Semantic Paper Workbench — Sprint 1 Demo
   Vanilla JS controller. No build step, no framework.
   API contracts per the FE-UI brief.
   All user/API-derived strings pass through escapeHtml() before
   being inserted into the DOM. Template literals only embed
   either static markup or values that have just been escaped.
   ============================================================ */

(() => {
  "use strict";

  // --- Session ---------------------------------------------------------------
  const SESSION_ID = (() => {
    try {
      const k = "spw_session_id";
      let s = localStorage.getItem(k);
      if (!s) {
        s = "s-" + Math.random().toString(36).slice(2, 10);
        localStorage.setItem(k, s);
      }
      return s;
    } catch (e) {
      return "s-" + Math.random().toString(36).slice(2, 10);
    }
  })();

  // --- App state -------------------------------------------------------------
  const state = {
    expand: true,
    selectedPaper: null,      // PaperSummary
    paperId: null,            // returned by /api/ingest
    paper: null,              // hydrated /api/papers/{id}
    sentences: [],            // last summary sentences
    length: "paragraph",
    angle: "contribution",
    eventSource: null,        // ingest SSE
    summaryStream: null,      // summary SSE (token-streamed sentences)
    selection: null,          // { section_id, char_start, char_end, text }
    glossary: [],
  };

  // --- Element refs ----------------------------------------------------------
  const $ = (id) => document.getElementById(id);
  const el = {
    healthMode: $("health-mode"),
    healthBadge: $("health-badge"),

    searchForm: $("search-form"),
    searchInput: $("search-input"),
    expandToggle: $("expand-toggle"),
    searchResults: $("search-results"),
    searchEmpty: $("search-empty"),
    searchMeta: $("search-meta"),

    paneIngest: $("pane-ingest"),
    ingestStages: $("ingest-stages"),
    ingestNotice: $("ingest-notice"),

    paneSummary: $("pane-summary"),
    lengthPresets: $("length-presets"),
    anglePresets: $("angle-presets"),
    runSummary: $("run-summary"),
    summaryMeta: $("summary-meta"),
    summaryOutput: $("summary-output"),
    railContent: $("rail-content"),

    paneTranslation: $("pane-translation"),
    translationEmpty: $("translation-empty"),
    translationResults: $("translation-results"),
    glossaryPanel: $("glossary-panel"),
    glossaryList: $("glossary-list"),
    glossaryCount: $("glossary-count"),

    tooltip: $("translate-tooltip"),
    tooltipBtn: $("translate-trigger"),
  };

  // ---------------------------------------------------------------------------
  // Safe DOM helpers — every interpolation site MUST pass through escapeHtml.
  // setSafeMarkup() is a single audited surface for assembling escaped HTML.
  // ---------------------------------------------------------------------------
  const escapeHtml = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));

  // Replace a node's contents with a pre-escaped markup string. All callers
  // construct their templates by interpolating escapeHtml(...) values only.
  function setSafeMarkup(node, escapedMarkup) {
    // eslint-disable-next-line no-unsanitized/property
    node.innerHTML = escapedMarkup;
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  // ============================================================================
  // BOOT
  // ============================================================================
  document.addEventListener("DOMContentLoaded", () => {
    bindSearch();
    bindPresets();
    bindSummaryRun();
    bindSelectionTooltip();
    fetchHealth();
  });

  // ============================================================================
  // HEALTH
  // ============================================================================
  async function fetchHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("health " + res.status);
      const data = await res.json();
      const mode = data.llm_mode || "unknown";
      el.healthMode.textContent = mode;
      const isLive = /claude|live/i.test(mode);
      el.healthBadge.classList.remove("chip-blue", "chip-green", "chip-mute");
      el.healthBadge.classList.add(isLive ? "chip-green" : "chip-blue");
      el.healthBadge.querySelector(".dot").style.background =
        isLive ? "var(--green)" : "var(--blue)";
    } catch (err) {
      el.healthMode.textContent = "offline";
      el.healthBadge.title = "/api/health 호출 실패";
    }
  }

  // ============================================================================
  // PANE 1 — SEARCH
  // ============================================================================
  function bindSearch() {
    el.expandToggle.addEventListener("click", () => {
      state.expand = !state.expand;
      el.expandToggle.dataset.on = String(state.expand);
      const dot = document.createElement("span");
      dot.className = "dot";
      clear(el.expandToggle);
      el.expandToggle.appendChild(dot);
      el.expandToggle.appendChild(
        document.createTextNode(`쿼리 확장 ${state.expand ? "ON" : "OFF"}`),
      );
    });

    el.searchForm.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const query = el.searchInput.value.trim();
      if (!query) return;
      await runSearch(query);
    });
  }

  async function runSearch(query) {
    el.searchEmpty.classList.add("hidden");
    setSafeMarkup(el.searchResults, renderSkeletonResults(3));
    el.searchMeta.classList.add("hidden");

    let data;
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, limit: 8, expand: state.expand }),
      });
      if (!res.ok) throw new Error("search " + res.status);
      data = await res.json();
    } catch (err) {
      setSafeMarkup(el.searchResults, renderError(
        "검색 API 호출에 실패한다.",
        "백엔드 /api/search 구현을 기다리는 중일 수 있다. 상세: " + err.message,
      ));
      return;
    }

    const results = Array.isArray(data?.results) ? data.results : [];
    if (!results.length) {
      el.searchEmpty.classList.remove("hidden");
      el.searchEmpty.textContent = "검색 결과가 없다.";
      clear(el.searchResults);
      return;
    }

    el.searchMeta.classList.remove("hidden");
    const normalized = data.normalized
      ? `정규화 쿼리: ${escapeHtml(data.normalized)} · `
      : "";
    setSafeMarkup(el.searchMeta, `${normalized}${escapeHtml(String(results.length))}건`);

    setSafeMarkup(el.searchResults, results.map(renderResultCard).join(""));
    el.searchResults.querySelectorAll("[data-ingest-id]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = Number(btn.dataset.ingestId);
        startIngest(results[idx]);
      });
    });
  }

  function renderSkeletonResults(n) {
    const one = `<li class="result-card animate-pulse">
      <div class="h-4 w-3/4 rounded bg-[var(--bg-soft)] mb-3"></div>
      <div class="h-3 w-1/3 rounded bg-[var(--bg-soft)] mb-3"></div>
      <div class="h-3 w-full rounded bg-[var(--bg-soft)] mb-1"></div>
      <div class="h-3 w-11/12 rounded bg-[var(--bg-soft)]"></div>
    </li>`;
    return one.repeat(n);
  }

  function renderError(headline, detail) {
    return `<li class="result-card" style="border-color: var(--warn);">
      <div class="text-sm font-semibold" style="color: var(--warn);">${escapeHtml(headline)}</div>
      <div class="text-xs mt-1" style="color: var(--ink-soft);">${escapeHtml(detail)}</div>
    </li>`;
  }

  function renderResultCard(p, i) {
    const authorList = (p.authors || []).slice(0, 4).join(", ") +
      ((p.authors || []).length > 4 ? " 외" : "");
    const authors = escapeHtml(authorList || "저자 미상");
    const yr = p.year ? escapeHtml(String(p.year)) : "";
    const venue = p.venue ? ` · ${escapeHtml(p.venue)}` : "";
    const absRaw = (p.abstract || "").trim().slice(0, 220);
    const abs = escapeHtml(absRaw);
    const truncated = (p.abstract || "").length > 220 ? "…" : "";
    const sourceChipClass =
      (p.source || "").toLowerCase() === "arxiv" ? "chip-accent" : "chip-blue";
    const source = escapeHtml(p.source || "unknown");
    const title = escapeHtml(p.title || "(제목 없음)");
    const arxivUrl = p.arxiv_url ? escapeHtml(p.arxiv_url) : "";
    const pdfUrl = p.pdf_url ? escapeHtml(p.pdf_url) : "";
    const idx = escapeHtml(String(i));

    return `<li class="result-card">
      <div class="flex items-start justify-between gap-3">
        <h3 class="result-title">${title}</h3>
        <span class="chip ${sourceChipClass} shrink-0">${source}</span>
      </div>
      <div class="result-meta">${authors} · ${yr}${venue}</div>
      ${abs ? `<p class="result-abstract">${abs}${truncated}</p>` : ""}
      <div class="result-actions">
        ${arxivUrl ? `<a class="btn-ghost" href="${arxivUrl}" target="_blank" rel="noopener">초록</a>` : ""}
        ${pdfUrl ? `<a class="btn-ghost" href="${pdfUrl}" target="_blank" rel="noopener">PDF</a>` : ""}
        <button type="button" class="btn-accent" data-ingest-id="${idx}" style="font-size:12px; padding:6px 14px;">
          PDF 요약
        </button>
      </div>
    </li>`;
  }

  // ============================================================================
  // PANE 2 — INGEST (SSE)
  // ============================================================================
  async function startIngest(paper) {
    state.selectedPaper = paper;
    state.paperId = null;
    state.paper = null;
    state.sentences = [];
    closeEventSource();

    el.paneIngest.classList.remove("hidden");
    el.paneSummary.classList.add("hidden");
    el.paneTranslation.classList.add("hidden");
    el.ingestNotice.classList.add("hidden");
    resetStages();
    el.paneIngest.scrollIntoView({ behavior: "smooth", block: "start" });

    let data;
    try {
      const res = await fetch("/api/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(paper),
      });
      if (!res.ok) throw new Error("ingest " + res.status);
      data = await res.json();
    } catch (err) {
      showIngestNotice("인입 API 호출에 실패한다: " + err.message, "warn");
      return;
    }

    state.paperId = data.paper_id;
    const streamUrl = data.stream_url || `/api/ingest/${encodeURIComponent(data.paper_id)}/events`;
    openIngestStream(streamUrl);
  }

  function resetStages() {
    el.ingestStages.querySelectorAll(".stage").forEach((s) => {
      s.dataset.state = "pending";
    });
    stageQueue.lastFireAt = 0;
  }

  function setStageState(stage, value) {
    const node = el.ingestStages.querySelector(`.stage[data-stage="${stage}"]`);
    if (node) node.dataset.state = value;
  }

  // Abstract-only ingest completes in <100ms server-side, so every SSE
  // event reaches the FE almost simultaneously. Without spacing, each
  // stage's `active` state flips to `done` before the @keyframes pulse
  // animation has a chance to render. We hold each stage's `active`
  // state for `MIN_DWELL_MS` so the pulse is actually visible.
  // CSS pulse cycle is 1.2s; dwell ≈ 75% of that so the user sees most of
  // one full breathing cycle before the next stage takes over.
  const STAGE_MIN_DWELL_MS = 900;
  const stageQueue = {
    lastFireAt: 0,
    /** Schedule `fn` to run after at least `STAGE_MIN_DWELL_MS` since the previous queued fn. */
    enqueue(fn) {
      const now = performance.now();
      const fireAt = Math.max(now, this.lastFireAt + STAGE_MIN_DWELL_MS);
      this.lastFireAt = fireAt;
      const delay = fireAt - now;
      if (delay <= 0) fn();
      else setTimeout(fn, delay);
    },
    /** Wait until the queue has fully drained (for awaiting the final state before hydration). */
    drained() {
      const now = performance.now();
      const wait = Math.max(0, this.lastFireAt - now);
      return new Promise((resolve) => setTimeout(resolve, wait));
    },
  };

  function openIngestStream(url) {
    closeEventSource();
    try {
      const es = new EventSource(url);
      state.eventSource = es;

      es.addEventListener("progress", (ev) => {
        const payload = safeJson(ev.data) || {};
        applyProgress(payload);
      });

      es.addEventListener("done", async (ev) => {
        const payload = safeJson(ev.data) || {};
        const noticeText = payload?.notice || payload?.message;
        // Enqueue the terminal "all done" through the same queue so the
        // earlier active-stage pulses get their full dwell time.
        stageQueue.enqueue(() => {
          ["fetch", "parse", "chunk", "done"].forEach((s) => setStageState(s, "done"));
          if (noticeText) showIngestNotice(noticeText, "info");
        });
        closeEventSource();
        await stageQueue.drained();
        await hydratePaper(state.paperId);
      });

      es.addEventListener("failed", (ev) => {
        const payload = safeJson(ev.data) || {};
        const failedStage = STAGE_ALIAS[payload?.stage] || payload?.stage || "fetch";
        stageQueue.enqueue(() => {
          setStageState(failedStage, "failed");
          showIngestNotice(`인입 실패: ${payload?.message || "원인 미상"}`, "warn");
        });
        closeEventSource();
      });

      // Default handler in case server sends untyped messages.
      es.onmessage = (ev) => {
        const payload = safeJson(ev.data) || {};
        if (payload?.stage) applyProgress(payload);
      };

      es.onerror = () => {
        showIngestNotice("SSE 스트림 연결이 끊겼다. 백엔드 구현을 확인한다.", "warn");
        closeEventSource();
      };
    } catch (err) {
      showIngestNotice("EventSource 생성 실패: " + err.message, "warn");
    }
  }

  // Backend uses topic-namespaced stage IDs ("ingest.fetching", …).
  // FE renders a 4-step strip ("fetch" → "parse" → "chunk" → "done").
  // This alias keeps the two contracts decoupled.
  const STAGE_ALIAS = {
    "ingest.started":  "fetch",
    "ingest.fetching": "fetch",
    "ingest.parsing":  "parse",
    "ingest.chunking": "chunk",
    "ingest.done":     "done",
    "ingest.failed":   null,
  };

  function applyProgress(payload) {
    const order = ["fetch", "parse", "chunk", "done"];
    const raw = payload.stage;
    const stage = STAGE_ALIAS[raw] !== undefined ? STAGE_ALIAS[raw] : raw;
    if (!stage || !order.includes(stage)) return;
    const idx = order.indexOf(stage);
    const noticeText = payload.notice || payload.message;
    // Run the DOM mutation through the dwell queue so each active state
    // gets at least one full pulse cycle on-screen, even when SSE events
    // arrive back-to-back (abstract-only ingest fires in <100ms total).
    stageQueue.enqueue(() => {
      for (let i = 0; i < idx; i++) setStageState(order[i], "done");
      setStageState(stage, payload.status === "done" ? "done" : "active");
      if (noticeText) showIngestNotice(noticeText, "info");
    });
  }

  function showIngestNotice(text, kind) {
    el.ingestNotice.textContent = text; // textContent: safe for arbitrary strings.
    el.ingestNotice.classList.remove("hidden");
    el.ingestNotice.style.color = kind === "warn" ? "var(--warn)" : "var(--ink-soft)";
    el.ingestNotice.style.background = kind === "warn" ? "var(--warn-soft)" : "var(--bg-soft)";
  }

  function closeEventSource() {
    if (state.eventSource) {
      try { state.eventSource.close(); } catch (e) { /* noop */ }
      state.eventSource = null;
    }
  }

  function safeJson(s) {
    try { return JSON.parse(s); } catch (e) { return null; }
  }

  // ============================================================================
  // HYDRATE PAPER (after ingest done)
  // ============================================================================
  async function hydratePaper(paperId) {
    let paper;
    try {
      const res = await fetch(`/api/papers/${encodeURIComponent(paperId)}`);
      if (!res.ok) throw new Error("paper " + res.status);
      paper = await res.json();
    } catch (err) {
      showIngestNotice(
        "논문 본문 로드 실패: " + err.message + " — abstract-only로 진행한다.",
        "warn",
      );
      paper = {
        summary: state.selectedPaper,
        sections: [{
          section_id: "abstract",
          title: "Abstract",
          paragraphs: [state.selectedPaper?.abstract || "(초록 없음)"],
        }],
        chunks: [],
      };
      showIngestNotice("GROBID off → abstract-only fallback", "info");
    }

    state.paper = paper;
    renderRail(paper);
    el.paneSummary.classList.remove("hidden");
    el.paneSummary.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderRail(paper) {
    const sections = paper?.sections || [];
    if (!sections.length) {
      setSafeMarkup(el.railContent,
        `<div class="text-sm text-[var(--ink-mute)]">섹션 정보가 없다.</div>`);
      return;
    }
    const html = sections.map((s) => {
      // Backend Section.paragraphs (list[str]) is the source of truth; collapse
      // into a single paragraph-separated block for the rail. Tolerate a stray
      // .text field too so the local fallback path keeps working if it drifts.
      const body = Array.isArray(s.paragraphs) && s.paragraphs.length
        ? s.paragraphs.join("\n\n")
        : (s.text || "");
      const sid = s.section_id || "?";
      const anchor = escapeHtml(`[§${sid}]`);
      const title = escapeHtml(s.title || "(untitled)");
      const text = escapeHtml(body.trim());
      const sidAttr = escapeHtml(sid);
      return `<div class="rail-section" data-anchor="${sidAttr}">
        <div class="rail-section-header">
          <div class="rail-anchor">${anchor}</div>
          <div class="rail-title">${title}</div>
          <button type="button" class="rail-summarize-btn" data-section-id="${sidAttr}" title="이 섹션만 요약한다">
            이 섹션만 요약
          </button>
        </div>
        <div class="rail-text">${text}</div>
      </div>`;
    }).join("");
    setSafeMarkup(el.railContent, html);

    // Wire each per-section summarize button to runSummary(section_id).
    el.railContent.querySelectorAll(".rail-summarize-btn").forEach((btn) => {
      btn.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const sid = btn.dataset.sectionId;
        if (!sid) return;
        runSummary({ sectionId: sid, sectionTitle: btn.closest(".rail-section")?.querySelector(".rail-title")?.textContent.trim() });
      });
    });
  }

  // ============================================================================
  // PANE 3 — SUMMARY
  // ============================================================================
  function bindPresets() {
    const bind = (root, key) => {
      root.addEventListener("click", (ev) => {
        const btn = ev.target.closest(".preset-btn");
        if (!btn) return;
        root.querySelectorAll(".preset-btn").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        state[key] = btn.dataset.value;
      });
    };
    bind(el.lengthPresets, "length");
    bind(el.anglePresets, "angle");
  }

  function bindSummaryRun() {
    el.runSummary.addEventListener("click", async () => {
      if (!state.paperId) return;
      await runSummary();
    });
  }

  async function runSummary(opts) {
    const sectionId = opts?.sectionId || null;
    const sectionTitle = opts?.sectionTitle || null;
    el.runSummary.disabled = true;
    el.summaryMeta.textContent = sectionId
      ? `섹션 "${sectionTitle || sectionId}" 요약 스트리밍 중…`
      : "스트리밍 중…";
    setSafeMarkup(el.summaryOutput, renderSummarySkeleton());

    // Tear down any prior summary stream before opening a new one.
    if (state.summaryStream) {
      try { state.summaryStream.close(); } catch (_) { /* ignore */ }
      state.summaryStream = null;
    }

    state.sentences = [];
    const t0 = performance.now();
    const qs = {
      paper_id: state.paperId,
      length: state.length,
      angle: state.angle,
      session_id: SESSION_ID,
    };
    if (sectionId) qs.section_id = sectionId;
    const params = new URLSearchParams(qs);
    const es = new EventSource(`/api/summary/stream?${params.toString()}`);
    state.summaryStream = es;

    es.addEventListener("sentence", (ev) => {
      const payload = safeJson(ev.data) || {};
      const s = payload.sentence;
      if (!s || typeof s.text !== "string") return;
      state.sentences.push(s);
      renderSummary(state.sentences);
      el.summaryMeta.textContent = `스트리밍 중… ${state.sentences.length}문장 도착`;
    });

    es.addEventListener("done", (ev) => {
      const payload = safeJson(ev.data) || {};
      const latency = (payload.latency_ms != null) ? ` · ${payload.latency_ms}ms` : ` · ${Math.round(performance.now() - t0)}ms`;
      const model = payload.model ? ` · ${payload.model}` : "";
      const gloss = Array.isArray(payload.glossary_additions) && payload.glossary_additions.length
        ? ` · glossary +${payload.glossary_additions.length}`
        : "";
      const scope = sectionId ? ` · 섹션 [§${sectionId}]` : "";
      el.summaryMeta.textContent = `스트림 완료${scope}${latency}${model}${gloss}`;
      el.runSummary.disabled = false;
      try { es.close(); } catch (_) { /* ignore */ }
      state.summaryStream = null;
    });

    es.addEventListener("failed", (ev) => {
      const payload = safeJson(ev.data) || {};
      setSafeMarkup(el.summaryOutput,
        `<div class="text-sm" style="color: var(--warn);">요약 스트림 실패: ${escapeHtml(payload.message || "원인 미상")}</div>`);
      el.summaryMeta.textContent = "";
      el.runSummary.disabled = false;
      try { es.close(); } catch (_) { /* ignore */ }
      state.summaryStream = null;
    });

    es.onerror = () => {
      // Browser closes the connection cleanly after our `done`; only flag
      // an error if no sentences arrived at all.
      if (!state.sentences.length && el.runSummary.disabled) {
        setSafeMarkup(el.summaryOutput,
          `<div class="text-sm" style="color: var(--warn);">SSE 스트림 연결이 끊겼다.</div>`);
        el.summaryMeta.textContent = "";
        el.runSummary.disabled = false;
      }
      try { es.close(); } catch (_) { /* ignore */ }
      state.summaryStream = null;
    };
  }

  function renderSummarySkeleton() {
    return `<div class="space-y-3 animate-pulse">
      <div class="h-4 w-full rounded bg-[var(--bg-card)] border border-[var(--line)]"></div>
      <div class="h-4 w-11/12 rounded bg-[var(--bg-card)] border border-[var(--line)]"></div>
      <div class="h-4 w-10/12 rounded bg-[var(--bg-card)] border border-[var(--line)]"></div>
    </div>`;
  }

  function renderSummary(sentences) {
    if (!sentences.length) {
      setSafeMarkup(el.summaryOutput,
        `<div class="text-sm text-[var(--ink-mute)]">요약 결과가 없다.</div>`);
      return;
    }

    const html = sentences.map((s, i) => {
      const cls = verifyClass(s.verify_label);
      const labelText = verifyLabelText(s.verify_label);
      // raw section_id is the key that matches data-anchor on the rail;
      // display form wraps it in [§…] (AGENTS.md §6.1).
      const sid = s.anchor?.section_id || s.anchor?.section || "?";
      const anchor = escapeHtml(sid);
      const anchorDisplay = escapeHtml(`[§${sid}]`);
      const text = escapeHtml(s.text || "");
      const conf = escapeHtml(String(s.confidence ?? "—"));
      const idx = escapeHtml(String(i));
      return `<span class="summary-sentence" data-idx="${idx}" data-anchor="${anchor}">
        ${text}
        <span class="anchor-tag">${anchorDisplay}</span>
        <span class="verify-badge ${cls}" title="confidence: ${conf}">${labelText}</span>
      </span>`;
    }).join(" ");
    setSafeMarkup(el.summaryOutput, html);

    // hover/click bridges to rail
    el.summaryOutput.querySelectorAll(".summary-sentence").forEach((node) => {
      node.addEventListener("mouseenter", () => highlightRail(node.dataset.anchor, true));
      node.addEventListener("mouseleave", () => highlightRail(node.dataset.anchor, false));
      node.addEventListener("click", () => {
        el.summaryOutput.querySelectorAll(".summary-sentence")
          .forEach((n) => n.classList.remove("is-active"));
        node.classList.add("is-active");
        scrollRailTo(node.dataset.anchor);
      });
    });
  }

  function verifyClass(label) {
    switch (label) {
      case "SUPPORTED":            return "verify-supported";
      case "PARTIALLY_SUPPORTED":  return "verify-partial";
      case "UNSUPPORTED":          return "verify-unsupported";
      default:                     return "verify-notfound";
    }
  }
  function verifyLabelText(label) {
    switch (label) {
      case "SUPPORTED":           return "supported";
      case "PARTIALLY_SUPPORTED": return "partial";
      case "UNSUPPORTED":         return "unsupported";
      default:                    return "not found";
    }
  }

  function highlightRail(anchor, on) {
    if (!anchor) return;
    const target = el.railContent.querySelector(`[data-anchor="${cssEscape(anchor)}"]`);
    if (target) target.classList.toggle("is-active", on);
  }
  function scrollRailTo(anchor) {
    const target = el.railContent.querySelector(`[data-anchor="${cssEscape(anchor)}"]`);
    if (target) {
      el.railContent.querySelectorAll(".rail-section")
        .forEach((n) => n.classList.remove("is-active"));
      target.classList.add("is-active");
      target.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }
  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/["\\]/g, "\\$&");
  }

  // ============================================================================
  // PANE 4 — TRANSLATION (selection-driven)
  // ============================================================================
  function bindSelectionTooltip() {
    document.addEventListener("mouseup", handleSelectionMaybe);
    document.addEventListener("selectionchange", () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed) hideTooltip();
    });

    el.tooltipBtn.addEventListener("click", async () => {
      hideTooltip();
      if (state.selection) {
        await runTranslate(state.selection);
      }
    });

    document.addEventListener("scroll", hideTooltip, true);
  }

  function handleSelectionMaybe() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return hideTooltip();
    const text = sel.toString().trim();
    if (text.length < 2) return hideTooltip();

    // Selection must originate inside a rail-section's .rail-text node.
    const anchorNode = sel.anchorNode;
    const railText = anchorNode && (anchorNode.nodeType === 1
      ? anchorNode.closest?.(".rail-text")
      : anchorNode.parentElement?.closest?.(".rail-text"));
    if (!railText) return hideTooltip();

    const sectionEl = railText.closest(".rail-section");
    const section_id = sectionEl?.dataset.anchor || "§?";
    const full = railText.textContent || "";
    const char_start = Math.max(0, full.indexOf(text));
    const char_end = char_start + text.length;

    state.selection = { section_id, char_start, char_end, text };

    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return hideTooltip();

    el.tooltip.style.left = (rect.left + window.scrollX + rect.width / 2) + "px";
    el.tooltip.style.top  = (rect.top  + window.scrollY) + "px";
    el.tooltip.classList.remove("hidden");
  }

  function hideTooltip() {
    el.tooltip.classList.add("hidden");
  }

  async function runTranslate(selection) {
    el.paneTranslation.classList.remove("hidden");
    el.translationEmpty.classList.add("hidden");
    el.translationResults.classList.remove("hidden");

    // Build a placeholder card with DOM APIs (safest path).
    const pair = document.createElement("div");
    pair.className = "translation-pair";

    const enSide = document.createElement("div");
    enSide.className = "translation-side";
    const enLabel = document.createElement("div");
    enLabel.className = "side-label";
    enLabel.textContent = "English";
    const enText = document.createElement("div");
    enText.className = "side-text";
    enText.textContent = selection.text;
    enSide.appendChild(enLabel);
    enSide.appendChild(enText);

    const koSide = document.createElement("div");
    koSide.className = "translation-side";
    const koLabel = document.createElement("div");
    koLabel.className = "side-label";
    koLabel.textContent = "한국어";
    const koText = document.createElement("div");
    koText.className = "side-text ko text-[var(--ink-mute)]";
    koText.textContent = "번역 중…";
    koSide.appendChild(koLabel);
    koSide.appendChild(koText);

    pair.appendChild(enSide);
    pair.appendChild(koSide);

    const wrapper = document.createElement("div");
    wrapper.appendChild(pair);
    el.translationResults.prepend(wrapper);

    let data;
    try {
      const res = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paper_id: state.paperId,
          section_id: selection.section_id,
          char_start: selection.char_start,
          char_end: selection.char_end,
          session_id: SESSION_ID,
        }),
      });
      if (!res.ok) throw new Error("translate " + res.status);
      data = await res.json();
    } catch (err) {
      koText.classList.remove("text-[var(--ink-mute)]");
      koText.style.color = "var(--warn)";
      koText.textContent = "번역 API 호출 실패: " + err.message;
      return;
    }

    const english = data.english || selection.text;
    const korean = data.korean || "";
    const additions = Array.isArray(data.glossary_additions) ? data.glossary_additions : [];

    // Final card — koWithGloss is assembled from escaped pieces.
    const koWithGloss = applyGlossing(korean, additions);
    const cacheLabel = data.cache_hit ? "· cache hit" : "";

    const finalHtml = `
      <div class="translation-pair">
        <div class="translation-side">
          <div class="side-label">English ${escapeHtml(cacheLabel)}</div>
          <div class="side-text">${escapeHtml(english)}</div>
        </div>
        <div class="translation-side">
          <div class="side-label">한국어</div>
          <div class="side-text ko">${koWithGloss}</div>
        </div>
      </div>
      ${additions.length ? `
        <div class="mt-2 flex flex-wrap gap-2">
          <span class="text-[11px] text-[var(--ink-mute)] mr-1 self-center">glossary 추가:</span>
          ${additions.map(renderGlossChip).join("")}
        </div>` : ""}`;
    setSafeMarkup(wrapper, finalHtml);

    await refreshGlossary();
  }

  // §6.2 glossing: 한국어(English) — the (English) portion gets muted styling.
  function applyGlossing(korean, additions) {
    // Tokenize on each glossed Korean term so we never substring-replace
    // across user content. Result is composed of escaped fragments only.
    let pieces = [escapeHtml(korean)];
    additions.forEach((g) => {
      if (!g?.english || !g?.korean) return;
      const koEsc = escapeHtml(g.korean);
      const enEsc = escapeHtml(g.english);
      const glossed = `<span class="gloss-pair">${koEsc}<span class="gloss-en">(${enEsc})</span></span>`;
      pieces = pieces.flatMap((piece) => {
        if (typeof piece !== "string") return [piece];
        const idx = piece.indexOf(koEsc);
        if (idx === -1) return [piece];
        return [piece.slice(0, idx), { html: glossed }, piece.slice(idx + koEsc.length)];
      });
    });
    return pieces.map((p) => (typeof p === "string" ? p : p.html)).join("");
  }

  function renderGlossChip(g) {
    const ko = escapeHtml(g.korean || "");
    const en = escapeHtml(g.english || "");
    return `<span class="glossary-chip">${ko}<span class="glossary-en">(${en})</span></span>`;
  }

  async function refreshGlossary() {
    try {
      const res = await fetch(`/api/glossary/${encodeURIComponent(SESSION_ID)}`);
      if (!res.ok) throw new Error("glossary " + res.status);
      const list = await res.json();
      state.glossary = Array.isArray(list) ? list : [];
    } catch (err) {
      // soft-fail — keep previous
    }
    if (!state.glossary.length) {
      el.glossaryPanel.classList.add("hidden");
      return;
    }
    el.glossaryPanel.classList.remove("hidden");
    el.glossaryCount.textContent = `${state.glossary.length} terms`;
    setSafeMarkup(el.glossaryList, state.glossary.map(renderGlossChip).join(""));
  }
})();
