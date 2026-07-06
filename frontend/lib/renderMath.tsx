'use client';

// renderMath (D4 — doc-model rich view). Renders LaTeX with KaTeX. The doc-model carries
// formulas as LaTeX (display blocks) and inline math embedded as \( ... \) inside text.
// XSS: KaTeX escapes its input and emits trusted markup; `throwOnError: false` degrades a
// malformed expression to its (escaped) source instead of throwing. Surrounding prose is
// rendered as React text nodes (escaped), never as HTML.
//
// The KaTeX stylesheet lives here, not in each consumer — any view that renders math (the
// doc-model viewer, the paper-detail abstract) gets it by importing this module, so math is
// never shown with the unstyled fallback.
import 'katex/dist/katex.min.css';
import { Fragment } from 'react';
import katex from 'katex';

// A KaTeX macro map (`\name` -> expansion) from the doc-model's e-print preamble
// (`meta.macros`), so author-defined commands resolve instead of rendering as red
// unsupported-command errors.
export type MathMacros = Record<string, string>;

// Always-on fallback macros, merged UNDER any per-paper `meta.macros` (author defs win).
// Two classes of recurring breakage they fix:
//   1. Common blackboard-bold sets papers usually `\newcommand` but that can be missing from
//      the e-print preamble (a `.sty` LaTeXML did not bundle) — KaTeX has no default for these.
//   2. Non-math layout/formatting macros that ride into the alttext source (and into abstracts,
//      which carry no `meta.macros`) — defined as no-ops so KaTeX does not red-flag them.
// Author macros override these via the merge order, so a paper that redefines `\R` still wins.
const DEFAULT_MACROS: MathMacros = {
  '\\R': '\\mathbb{R}',
  '\\N': '\\mathbb{N}',
  '\\Z': '\\mathbb{Z}',
  '\\Q': '\\mathbb{Q}',
  '\\C': '\\mathbb{C}',
  // Layout/spacing no-ops (carry no math meaning).
  '\\centering': '',
  '\\raggedright': '',
  '\\raggedleft': '',
  '\\noindent': '',
  '\\par': '',
  '\\hfill': '',
  '\\vfill': '',
  '\\medskip': '',
  '\\smallskip': '',
  '\\bigskip': '',
  '\\newline': '',
  '\\protect': '',
  '\\xspace': '',
  // `physics` package (very common on arXiv) commands KaTeX has no default for, so an unhandled one
  // collapses the WHOLE formula to a placeholder. Each expansion below was verified to render (and
  // to be semantically faithful) against KaTeX; none override a KaTeX builtin (notably `\div` = ÷ is
  // left untouched — physics's divergence uses the distinct `\divergence`). The two *structural*
  // families — `\matrixquantity`/`\derivative` and their variants — can't be plain macros (delimiter
  // detection / variable arity); they are rewritten by `preprocessPhysics` below.
  //
  // Auto-sized bracket commands: the alttext keeps the literal delimiters, so expanding the command
  // to NOTHING leaves e.g. `(x)` — renders correctly, only losing the auto-sizing.
  '\\quantity': '',
  '\\qty': '',
  // Operators / functions.
  '\\tr': '\\operatorname{tr}',
  '\\trace': '\\operatorname{tr}',
  '\\Tr': '\\operatorname{Tr}',
  '\\rank': '\\operatorname{rank}',
  '\\Res': '\\operatorname{Res}',
  '\\erf': '\\operatorname{erf}',
  // Vector calculus (`\div` intentionally omitted — it is KaTeX's ÷).
  '\\grad': '\\nabla',
  '\\gradient': '\\nabla',
  '\\curl': '\\nabla\\times',
  '\\divergence': '\\nabla\\cdot',
  '\\laplacian': '\\nabla^2',
  // Differential `\dd` in integrals/derivatives.
  '\\dd': '\\mathrm{d}',
  // Vector decorations: bold / arrow / unit-hat.
  '\\vb': '\\mathbf',
  '\\va': '\\vec',
  '\\vu': '\\hat',
  // Absolute value / norm (brace-argument forms).
  '\\abs': '\\left\\lvert #1 \\right\\rvert',
  '\\absolutevalue': '\\left\\lvert #1 \\right\\rvert',
  '\\norm': '\\left\\lVert #1 \\right\\rVert',
  // Commutator / anticommutator / Poisson bracket.
  '\\comm': '\\left[#1,#2\\right]',
  '\\acomm': '\\left\\{#1,#2\\right\\}',
  '\\anticommutator': '\\left\\{#1,#2\\right\\}',
  '\\pb': '\\left\\{#1,#2\\right\\}',
  '\\poissonbracket': '\\left\\{#1,#2\\right\\}',
  // Order / big-O.
  '\\order': '\\mathcal{O}\\!\\left(#1\\right)',
  '\\bigO': '\\mathcal{O}\\!\\left(#1\\right)',
  '\\Order': '\\mathcal{O}\\!\\left(#1\\right)',
  // LaTeXML artifact: it renames `\left`/`\right` to `\originalleft`/`\originalright` in some
  // alttext, which KaTeX then rejects — map them straight back.
  '\\originalleft': '\\left',
  '\\originalright': '\\right',
  '\\leavevmode': '',
  // Blackboard-bold variants from `dsfont`/`bbm` (indicator function `\mathds{1}`, `\mathbbm{1}`);
  // KaTeX has no default, so fold them into its `\mathbb` (renders digits + letters).
  '\\mathds': '\\mathbb',
  '\\mathbbm': '\\mathbb',
  // Small-caps / nice-fraction text packages KaTeX lacks — degrade to plain text / a normal fraction
  // (faithful in content, not in the exact glyph styling).
  '\\textsc': '\\text{#1}',
  '\\nicefrac': '\\frac{#1}{#2}',
  // A few more recurring alttext leaks: physics `\differential` (like `\dd`), a `\boldmath` switch
  // (no-op in math), and the `\varmathbb` blackboard alias.
  '\\differential': '\\mathrm{d}',
  '\\boldmath': '',
  '\\varmathbb': '\\mathbb',
};

// Unsupported-but-harmless tokens degrade to their source in this muted tone (not alarming
// red). Surrounding valid math still renders normally; only the unresolved span is tinted.
const ERROR_COLOR = '#6b7280';

// Fail-soft fallback: some author LaTeX carries a construct KaTeX rejects with a *fatal* parse
// error (a braced ``\big{(}`` delimiter, an unknown macro, a stray ``&`` …). With
// `throwOnError:false` KaTeX renders the WHOLE expression as its raw source — a wall of
// backslashes that reads as broken. Rather than show that, we catch the throw and emit a compact,
// intentional-looking placeholder that carries the source in its tooltip (hover/long-press to
// inspect). Ingestion strips the known offenders, but the input is open-ended, so this guarantees
// no formula ever renders as backslash soup regardless of what slips through.
function escapeHtmlAttr(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fallbackHtml(latex: string, displayMode: boolean): string {
  const title = escapeHtmlAttr(latex);
  // Inline styles (not a CSS-module class) because this HTML is injected via dangerouslySetInnerHTML
  // into several consumers with independent stylesheets; inline keeps it self-contained + CSP-safe.
  const shared =
    'color:#6b7280;font-size:0.9em;border:1px dashed currentColor;border-radius:4px;' +
    'padding:0 0.35em;cursor:help;white-space:nowrap;';
  const style = displayMode ? `display:inline-block;${shared}` : shared;
  return (
    `<span role="img" aria-label="수식 (표시할 수 없음)" title="${title}" style="${style}">` +
    `수식</span>`
  );
}

// Memoize rendered LaTeX — katex.renderToString is a synchronous parse and the same
// expression re-renders on every parent re-render (e.g. when figure assets resolve, or a
// results table with many math cells re-renders). Keyed by (displayMode, latex); the input
// space is bounded by the paper's distinct expressions.
//
// The cache is per macro map: a given expression renders differently under different macros,
// and KaTeX *mutates* the `macros` object it is given (it writes `\gdef`-defined globals and
// caches expansions there).
//
// Per distinct `meta.macros` object we keep one mutable working copy (KaTeX may write to it,
// leaving the immutable doc-model object untouched) plus its own render cache, keyed off the
// object identity via a WeakMap. Mutation persisting across a paper's own expressions is correct
// — `\gdef` is document-global, and these all belong to one paper.
//
// Calls WITHOUT macros (every abstract, plus formulas with no preamble) must NOT share one
// mutable working object: they come from different papers, so a `\gdef` in one render would leak
// into every later default render. We therefore hand KaTeX a FRESH `DEFAULT_MACROS` copy per
// default-path call (isolating the mutation) while still sharing one render cache — the cache is
// keyed by the expression string, so identical expressions are never re-rendered.
const _defaultCache = new Map<string, string>();
const _byMacros = new WeakMap<MathMacros, { working: MathMacros; cache: Map<string, string> }>();

function entryFor(macros?: MathMacros): { working: MathMacros; cache: Map<string, string> } {
  if (!macros) return { working: { ...DEFAULT_MACROS }, cache: _defaultCache };
  let entry = _byMacros.get(macros);
  if (!entry) {
    // Author macros win over the fallbacks (merge order).
    entry = { working: { ...DEFAULT_MACROS, ...macros }, cache: new Map() };
    _byMacros.set(macros, entry);
  }
  return entry;
}

// ---------------------------------------------------------------------------
// physics-package STRUCTURAL macros. Unlike `\quantity`/`\tr` (pure macros, above), these take a
// delimiter-detected group (`\matrixquantity[…]` picks its matrix delimiters from the following
// bracket) or a variable number of arguments (`\derivative` has an optional order plus one OR two
// operands) — neither is expressible as a KaTeX macro. Left unhandled, KaTeX collapses the whole
// formula to a placeholder. A small brace/bracket-depth-aware scanner rewrites them to KaTeX-native
// `\begin{…matrix}` / `\frac` BEFORE rendering. Read-time, so it fixes already-stored doc-models
// with no re-ingest. Anything it does not recognise is left verbatim (KaTeX then decides).

// From an opening delimiter at `s[i]` (`(`, `[`, or `{`), return the substring up to its matching
// close and the index just past it — tracking nesting of the SAME delimiter and skipping over `{…}`
// groups and backslash-escaped chars, so a nested `[…]` (e.g. `[C]^{-1}` inside a matrix) or a `]`
// inside a brace group does not close it early. Null if unbalanced.
function readDelimGroup(s: string, i: number): { inner: string; end: number } | null {
  const open = s[i];
  const close = open === '(' ? ')' : open === '[' ? ']' : open === '{' ? '}' : '';
  if (!close) return null;
  if (open === '{') {
    let depth = 0;
    for (let j = i; j < s.length; j += 1) {
      const c = s[j];
      if (c === '\\') { j += 1; continue; } // escaped char (\{ \} \\) — never a delimiter
      if (c === '{') depth += 1;
      else if (c === '}') { depth -= 1; if (depth === 0) return { inner: s.slice(i + 1, j), end: j + 1 }; }
    }
    return null;
  }
  let depth = 0;
  let brace = 0;
  for (let j = i; j < s.length; j += 1) {
    const c = s[j];
    if (c === '\\') { j += 1; continue; }
    if (c === '{') brace += 1;
    else if (c === '}') brace -= 1;
    else if (brace === 0) {
      if (c === open) depth += 1;
      else if (c === close) { depth -= 1; if (depth === 0) return { inner: s.slice(i + 1, j), end: j + 1 }; }
    }
  }
  return null;
}

function skipSpace(s: string, i: number): number {
  while (i < s.length && /\s/.test(s[i])) i += 1;
  return i;
}

// The physics matrix delimiter selects the KaTeX matrix environment (its visible fences).
const MATRIX_ENV: Record<string, string> = { '(': 'pmatrix', '[': 'bmatrix', '{': 'matrix' };

// `\matrixquantity[a & b \\ c & d]` → `\begin{bmatrix} a & b \\ c & d \end{bmatrix}` (delimiter →
// environment via MATRIX_ENV). `\smatrixquantity`/`\smqty` (the "small" variant) are folded in here
// — rendered at full size, which is faithful in content if not in scale. Recurses into the body so a
// block matrix (nested matrixquantity) is rewritten too. A form with no following delimiter is left
// verbatim. The scan regex is declared per call (not hoisted) because the recursion would otherwise
// clobber a shared `lastIndex`.
function rewriteMatrixQuantity(s: string): string {
  const re = /\\(?:matrixquantity|smatrixquantity|mqty|smqty)\b\s*/g;
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    const dpos = skipSpace(s, m.index + m[0].length);
    const g = readDelimGroup(s, dpos);
    if (!g) continue; // no delimiter group → not the expected form; leave the token as-is
    const env = MATRIX_ENV[s[dpos]] ?? 'matrix';
    out += s.slice(last, m.index) + `\\begin{${env}}` + rewriteMatrixQuantity(g.inner) + `\\end{${env}}`;
    last = g.end;
    re.lastIndex = g.end;
  }
  return out + s.slice(last);
}

// `\derivative[n]{f}{x}` → `\frac{\mathrm{d}^{n} f}{\mathrm{d} x^{n}}` (order optional); the
// two-operand *operator* form `\derivative[n]{x}` → `\frac{\mathrm{d}^{n}}{\mathrm{d} x^{n}}`. The
// order is kept as written (this paper uses fractional/symbolic orders like `\alpha`, `-\alpha`).
// `\pdv`/`\partialderivative` are the same shape with `\partial` instead of `\mathrm{d}` (its command
// name is captured to pick the differential symbol). A form with no `{…}` operand is left verbatim.
function rewriteDerivative(s: string): string {
  const re = /\\(derivative|dv|partialderivative|pdv)\b\s*/g;
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    const d = m[1] === 'pdv' || m[1] === 'partialderivative' ? '\\partial' : '\\mathrm{d}';
    let i = skipSpace(s, m.index + m[0].length);
    let order: string | null = null;
    if (s[i] === '[') {
      const g = readDelimGroup(s, i);
      if (g) { order = g.inner; i = g.end; }
    }
    i = skipSpace(s, i);
    if (s[i] !== '{') continue; // no operand → not the expected form; leave verbatim
    const a = readDelimGroup(s, i);
    if (!a) continue;
    i = a.end;
    const j = skipSpace(s, i);
    let b: string | null = null;
    if (s[j] === '{') {
      const g = readDelimGroup(s, j);
      if (g) { b = g.inner; i = g.end; }
    }
    const ord = order ? `^{${order}}` : '';
    const repl =
      b !== null
        ? `\\frac{${d}${ord} ${a.inner}}{${d} ${b}${ord}}`
        : `\\frac{${d}${ord}}{${d} ${a.inner}${ord}}`;
    out += s.slice(last, m.index) + repl;
    last = i;
    re.lastIndex = i;
  }
  return out + s.slice(last);
}

// LaTeXML sometimes leaks a reference/citation command into a formula's alttext — a trailing
// `\cite[citep]{…}` inside a `\text{…}`, or a LaTeXML-internal `\lx@cref{creftype~refnum}{key}`
// cleveref (which takes TWO arguments). KaTeX has no such command, so the ONE stray token throws and
// collapses the WHOLE equation to the placeholder (observed on ~0.05% of formulas). These carry no
// math meaning, so strip the command plus its optional `[…]` and ALL of its balanced `{…}` arguments.
// Read-time, so it heals already-stored doc-models with no re-ingest.
const LEAKED_REF_RE = /\\(?:cite[a-z]*|ref|eqref|autoref|label|footnote|lx@[a-zA-Z@]+)\b/g;
function stripLeakedRefs(latex: string): string {
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  LEAKED_REF_RE.lastIndex = 0;
  while ((m = LEAKED_REF_RE.exec(latex))) {
    out += latex.slice(last, m.index);
    let i = skipSpace(latex, m.index + m[0].length);
    if (latex[i] === '[') {
      const g = readDelimGroup(latex, i); // optional [key] (e.g. \cite[citep]{…})
      if (g) i = g.end;
    }
    // Consume every consecutive brace argument: `\cite`/`\ref`/`\label` take one, `\lx@cref` two.
    for (;;) {
      const j = skipSpace(latex, i);
      if (latex[j] !== '{') break;
      const g = readDelimGroup(latex, j); // balanced {…} (may nest)
      if (!g) break;
      i = g.end;
    }
    last = i;
    LEAKED_REF_RE.lastIndex = i;
  }
  return out + latex.slice(last);
}

// `\scalebox{factor}{content}` / `\resizebox{w}{h}{content}` carry display-only sizing KaTeX has no
// equivalent for. Keep the content group (the last argument) and drop the size args so the math
// still renders (only the scaling is lost). A form without the expected arg count is left verbatim.
function rewriteScalebox(s: string): string {
  const re = /\\(scalebox|resizebox)\b\s*/g;
  let out = '';
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(s))) {
    const argc = m[1] === 'resizebox' ? 3 : 2; // resizebox{w}{h}{content}, scalebox{factor}{content}
    let i = m.index + m[0].length;
    const groups: { inner: string; end: number }[] = [];
    for (let k = 0; k < argc; k += 1) {
      i = skipSpace(s, i);
      if (s[i] !== '{') break;
      const g = readDelimGroup(s, i);
      if (!g) break;
      groups.push(g);
      i = g.end;
    }
    if (groups.length !== argc) continue; // not the expected shape → leave the token verbatim
    out += s.slice(last, m.index) + `{${groups[argc - 1].inner}}`;
    last = i;
    re.lastIndex = i;
  }
  return out + s.slice(last);
}

function preprocessLatex(latex: string): string {
  // Drop leaked citation/ref commands first (a `\cite` inside a `\text{}` would otherwise make the
  // whole formula throw); unwrap `\scalebox`/`\resizebox` to their content; normalize the `split`
  // environment (KaTeX has no `split`) to the equivalent `aligned`. Then matrices before derivatives:
  // a `\derivative` may sit inside a `\matrixquantity` cell, and rewriting the matrix first flattens
  // it into the string the derivative pass then scans.
  const s = rewriteScalebox(stripLeakedRefs(latex))
    .replace(/\\begin\{split\}/g, '\\begin{aligned}')
    .replace(/\\end\{split\}/g, '\\end{aligned}');
  return rewriteDerivative(rewriteMatrixQuantity(s));
}

function toHtml(latex: string, displayMode: boolean, macros?: MathMacros): string {
  const { working, cache } = entryFor(macros);
  const cacheKey = `${displayMode ? 'd' : 'i'}:${latex}`;
  const hit = cache.get(cacheKey);
  if (hit !== undefined) return hit;
  // throwOnError:true so a parse error is caught here (→ compact placeholder). KaTeX parse errors
  // are all-or-nothing — with throwOnError:false it would render the WHOLE expression as raw
  // backslash source, so catching the throw and substituting the placeholder is a strict
  // improvement (same formulas affected, no source wall). errorColor still tints any non-fatal
  // strict-mode leniencies KaTeX resolves without throwing.
  let html: string;
  try {
    html = katex.renderToString(preprocessLatex(latex), {
      displayMode,
      throwOnError: true,
      errorColor: ERROR_COLOR,
      strict: false,
      output: 'html',
      macros: working,
    });
  } catch {
    // Tooltip carries the ORIGINAL source (pre-rewrite), so a hover shows what the author wrote.
    html = fallbackHtml(latex, displayMode);
  }
  cache.set(cacheKey, html);
  return html;
}

/** A display (block-level) equation. */
export function MathDisplay({ latex, macros }: { latex: string; macros?: MathMacros }) {
  return <span dangerouslySetInnerHTML={{ __html: toHtml(latex, true, macros) }} />;
}

type MathToken = { start: number; end: number; latex: string; display: boolean };

function isWhitespace(char: string | undefined): boolean {
  return char === undefined || /\s/.test(char);
}

function findClosingDollar(text: string, from: number): number {
  for (let i = from; i < text.length; i += 1) {
    if (text[i] === '$' && text[i - 1] !== '\\' && !isWhitespace(text[i - 1])) return i;
  }
  return -1;
}

// Math delimiters, in match-priority order: display `$$…$$` / `\[…\]`, then inline `\(…\)`
// / `$…$`. Scanning avoids regex backtracking on LaTeX-heavy strings with many escaped chars.
function findNextMath(text: string, from: number): MathToken | null {
  for (let i = from; i < text.length; i += 1) {
    if (text.startsWith('$$', i)) {
      const end = text.indexOf('$$', i + 2);
      if (end !== -1)
        return { start: i, end: end + 2, latex: text.slice(i + 2, end), display: true };
      i += 1;
      continue;
    }
    if (text.startsWith('\\[', i)) {
      const end = text.indexOf('\\]', i + 2);
      if (end !== -1)
        return { start: i, end: end + 2, latex: text.slice(i + 2, end), display: true };
      i += 1;
      continue;
    }
    if (text.startsWith('\\(', i)) {
      const end = text.indexOf('\\)', i + 2);
      if (end !== -1)
        return { start: i, end: end + 2, latex: text.slice(i + 2, end), display: false };
      i += 1;
      continue;
    }
    if (text[i] === '$' && !isWhitespace(text[i + 1])) {
      const end = findClosingDollar(text, i + 1);
      if (end !== -1)
        return { start: i, end: end + 1, latex: text.slice(i + 1, end), display: false };
    }
  }
  return null;
}

/** Render text that may contain inline/display math (`$…$`, `$$…$$`, `\(…\)`, `\[…\]`) into
 * React nodes. Prose segments stay React-escaped; only the math segments become KaTeX markup. */
export function renderInlineMath(text: string, macros?: MathMacros): React.ReactNode {
  if (!text.includes('$') && !text.includes('\\(') && !text.includes('\\[')) return text;
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  while (last < text.length) {
    const token = findNextMath(text, last);
    if (!token) break;
    if (token.start > last)
      nodes.push(<Fragment key={key++}>{text.slice(last, token.start)}</Fragment>);
    nodes.push(
      <span
        key={key++}
        dangerouslySetInnerHTML={{ __html: toHtml(token.latex, token.display, macros) }}
      />,
    );
    last = token.end;
  }
  if (last === 0) return text; // no delimiter actually matched (e.g. a lone `$`)
  if (last < text.length) nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  return nodes;
}

// **bold** spans (non-greedy). Bold may wrap math, so each part is still run through
// renderInlineMath. Used inside renderRichText for LLM summary prose.
const BOLD = /\*\*([\s\S]+?)\*\*/g;

/** Normalize the literal `\n`/`\t` escape artifacts that the backend's JSON re-escaping leaves in
 * math-heavy fields, back into a real newline / space — but NOT when the backslash starts a LaTeX
 * command (`\nabla`, `\theta`, `\times`), so math survives. Shared by both summary renderers so an
 * inline field (tldr, contributions, reproducibility) restores its line breaks the same way the
 * block renderer does — without this, a legitimately-escaped `\n` shows as a literal in the inline
 * fields. `.body`'s `white-space: pre-wrap` then renders the real newline as a break. */
function normalizeEscapeArtifacts(text: string): string {
  return text.replace(/\\n(?![a-zA-Z])/g, '\n').replace(/\\t(?![a-zA-Z])/g, ' ');
}

/** Inline render: `**bold**` + math, no block structure. For short single-line fields and list
 * items (already inside an <li>). */
export function renderInlineRich(text: string, macros?: MathMacros): React.ReactNode {
  const t = normalizeEscapeArtifacts(text);
  if (!t.includes('**')) return renderInlineMath(t, macros);
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of t.matchAll(BOLD)) {
    const idx = m.index ?? 0;
    if (idx > last) {
      nodes.push(<Fragment key={key++}>{renderInlineMath(t.slice(last, idx), macros)}</Fragment>);
    }
    nodes.push(<strong key={key++}>{renderInlineMath(m[1], macros)}</strong>);
    last = idx + m[0].length;
  }
  if (last < t.length) {
    nodes.push(<Fragment key={key++}>{renderInlineMath(t.slice(last), macros)}</Fragment>);
  }
  return nodes;
}

/** Render an LLM summary field as lightweight markdown + math: blank-line paragraphs, `-`/`*`
 * bullet lists, `**bold**`, and inline/display math. Also normalizes literal `\n`/`\t` escape
 * artifacts (left by re-escaping math-heavy JSON) into real breaks/space — but NOT when they start
 * a LaTeX command (`\nabla`, `\theta`, `\times`), so math survives. Returns block elements, so the
 * caller must place it in a block container (a <div>, not a <p>). */
export function renderRichText(text: string, macros?: MathMacros): React.ReactNode {
  if (!text) return null;
  const normalized = normalizeEscapeArtifacts(text);
  const blocks = normalized
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean);
  if (blocks.length === 0) return null;
  return blocks.map((block, bi) => {
    const lines = block.split('\n').map((l) => l.trimEnd());
    const nonEmpty = lines.filter((l) => l.trim());
    const isBullets = nonEmpty.length > 0 && nonEmpty.every((l) => /^\s*[-*•]\s+/.test(l));
    if (isBullets) {
      const items = nonEmpty.map((l) => l.replace(/^\s*[-*•]\s+/, ''));
      return (
        <ul key={bi}>
          {items.map((it, ii) => (
            <li key={ii}>{renderInlineRich(it, macros)}</li>
          ))}
        </ul>
      );
    }
    return (
      <p key={bi}>
        {lines.map((l, li) => (
          <Fragment key={li}>
            {li > 0 ? <br /> : null}
            {renderInlineRich(l, macros)}
          </Fragment>
        ))}
      </p>
    );
  });
}
