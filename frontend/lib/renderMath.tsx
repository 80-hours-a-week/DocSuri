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
};

// Unsupported-but-harmless tokens degrade to their source in this muted tone (not alarming
// red). Surrounding valid math still renders normally; only the unresolved span is tinted.
const ERROR_COLOR = '#6b7280';

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

function toHtml(latex: string, displayMode: boolean, macros?: MathMacros): string {
  const { working, cache } = entryFor(macros);
  const cacheKey = `${displayMode ? 'd' : 'i'}:${latex}`;
  const hit = cache.get(cacheKey);
  if (hit !== undefined) return hit;
  const html = katex.renderToString(latex, {
    displayMode,
    throwOnError: false,
    errorColor: ERROR_COLOR,
    strict: false,
    output: 'html',
    macros: working,
  });
  cache.set(cacheKey, html);
  return html;
}

/** A display (block-level) equation. */
export function MathDisplay({ latex, macros }: { latex: string; macros?: MathMacros }) {
  return <span dangerouslySetInnerHTML={{ __html: toHtml(latex, true, macros) }} />;
}

// Math delimiters, in match-priority order: display `$$…$$` / `\[…\]`, then inline `\(…\)`
// / `$…$`. arXiv abstracts use TeX `$…$` (e.g. "$K$", "$\beta\leq 1$"), the doc-model uses
// `\(…\)` — both are supported. The `$…$` arm forbids whitespace just inside the delimiters
// (`(?!\s)` / `(?<!\s)`) so prose prices like "$5 and $10" don't get parsed as math.
// Group: 1=$$ display, 2=\[ display, 3=\( inline, 4=$ inline.
const MATH =
  /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$(?!\s)((?:\\.|[^$])+?)(?<!\s)\$/g;

/** Render text that may contain inline/display math (`$…$`, `$$…$$`, `\(…\)`, `\[…\]`) into
 * React nodes. Prose segments stay React-escaped; only the math segments become KaTeX markup. */
export function renderInlineMath(text: string, macros?: MathMacros): React.ReactNode {
  if (!text.includes('$') && !text.includes('\\(') && !text.includes('\\[')) return text;
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(MATH)) {
    const idx = m.index ?? 0;
    if (idx > last) nodes.push(<Fragment key={key++}>{text.slice(last, idx)}</Fragment>);
    const display = m[1] !== undefined || m[2] !== undefined;
    const latex = m[1] ?? m[2] ?? m[3] ?? m[4] ?? '';
    nodes.push(
      <span key={key++} dangerouslySetInnerHTML={{ __html: toHtml(latex, display, macros) }} />,
    );
    last = idx + m[0].length;
  }
  if (last === 0) return text; // no delimiter actually matched (e.g. a lone `$`)
  if (last < text.length) nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  return nodes;
}

// **bold** spans (non-greedy). Bold may wrap math, so each part is still run through
// renderInlineMath. Used inside renderRichText for LLM summary prose.
const BOLD = /\*\*([\s\S]+?)\*\*/g;

/** Inline render: `**bold**` + math, no block structure. For short single-line fields and list
 * items (already inside an <li>). */
export function renderInlineRich(text: string, macros?: MathMacros): React.ReactNode {
  if (!text.includes('**')) return renderInlineMath(text, macros);
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(BOLD)) {
    const idx = m.index ?? 0;
    if (idx > last) {
      nodes.push(<Fragment key={key++}>{renderInlineMath(text.slice(last, idx), macros)}</Fragment>);
    }
    nodes.push(<strong key={key++}>{renderInlineMath(m[1], macros)}</strong>);
    last = idx + m[0].length;
  }
  if (last < text.length) {
    nodes.push(<Fragment key={key++}>{renderInlineMath(text.slice(last), macros)}</Fragment>);
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
  const normalized = text.replace(/\\n(?![a-zA-Z])/g, '\n').replace(/\\t(?![a-zA-Z])/g, ' ');
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
