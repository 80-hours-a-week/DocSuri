import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import fc from 'fast-check';
import { MathDisplay, renderInlineMath, renderInlineRich, renderRichText } from '@/lib/renderMath';

// renderInlineMath turns TeX delimiters in plain text into KaTeX markup. The arXiv abstract
// convention is `$…$` (inline) / `$$…$$` (display); the doc-model also uses `\(…\)`.
function html(node: React.ReactNode): HTMLElement {
  const { container } = render(<>{node}</>);
  return container;
}

describe('fail-soft fallback (no raw backslash source on a KaTeX parse error)', () => {
  it('renders a compact placeholder instead of the source when a display formula cannot parse', () => {
    // `\big{(}` (brace-wrapped delimiter) is a fatal KaTeX parse error — the exact break the user
    // saw. It must NOT spill its backslash source onto the page.
    const c = html(<MathDisplay latex={String.raw`2\big{(}x\Big{]}`} />);
    expect(c.textContent).toBe('수식');
    expect(c.textContent).not.toContain('\\big');
    // Source is preserved for inspection in the tooltip, HTML-escaped (no injection).
    const chip = c.querySelector('[role="img"]') as HTMLElement;
    expect(chip.getAttribute('title')).toContain('\\big{(}');
  });

  it('escapes angle brackets in the tooltip so a hostile source cannot inject markup', () => {
    const c = html(<MathDisplay latex={String.raw`\big{<}<script>`} />);
    expect(c.querySelector('script')).toBeNull();
  });

  it('still renders valid math normally (fallback only on failure)', () => {
    const c = html(<MathDisplay latex={String.raw`\frac{a}{b}`} />);
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toBe('수식');
  });

  it('renders a formula whose alttext leaked a `\\cite` command (strip it, do not collapse)', () => {
    // Real @6 doc-model breakage: LaTeXML leaked a trailing `\cite[citep]{…}` (nested braces) into
    // eq (30). KaTeX has no `\cite`, so the WHOLE equation collapsed to the 수식 placeholder. The
    // leaked citation carries no math meaning → strip it and render the real expression.
    const latex = String.raw`\ln[2\pi I_{0}(c)]\quad\text{\cite[citep]{({A}{mardia2009}{{, }}{})}}`;
    const c = html(<MathDisplay latex={latex} />);
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toBe('수식');
  });
});

describe('renderInlineMath', () => {
  it('renders arXiv `$…$` inline math as KaTeX, not raw source', () => {
    const c = html(renderInlineMath('a convex combination of $K$ base measures'));
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('$K$');
    expect(c.textContent).toContain('base measures');
  });

  it('handles `$β\\leq 1$` (symbols + commands)', () => {
    const c = html(renderInlineMath('matches when $β\\leq 1$.'));
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('\\leq');
  });

  it('still renders the doc-model `\\(…\\)` form', () => {
    const c = html(renderInlineMath('inline \\(x^2\\) here'));
    expect(c.querySelector('.katex')).not.toBeNull();
  });

  it('renders `$$…$$` in display mode', () => {
    const c = html(renderInlineMath('$$E = mc^2$$'));
    expect(c.querySelector('.katex-display')).not.toBeNull();
  });

  it('leaves prose currency like "$5 and $10" untouched', () => {
    const c = html(renderInlineMath('costs $5 and $10 total'));
    expect(c.querySelector('.katex')).toBeNull();
    expect(c.textContent).toBe('costs $5 and $10 total');
  });

  it('scans escaped characters in dollar math without regex backtracking', () => {
    const escaped = Array.from({ length: 200 }, () => '\\#').join('');
    const c = html(renderInlineMath(`noise $a ${escaped} b$ done`));
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).toContain('done');
  });

  it('keeps bounded escaped dollar math renderable across generated inputs', () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom('\\#', '\\$', '\\_', 'x', ' ', '+'), {
          maxLength: 80,
        }),
        (parts) => {
          const c = html(renderInlineMath(`before $a${parts.join('')}b$ after`));
          expect(c.querySelector('.katex')).not.toBeNull();
          expect(c.textContent).toContain('after');
          expect(c.textContent).not.toContain('$a');
        },
      ),
      { numRuns: 50 },
    );
  });

  it('returns plain text when there is no math', () => {
    expect(renderInlineMath('no math here')).toBe('no math here');
  });

  it('resolves a custom macro from meta.macros instead of showing the raw command', () => {
    // Without the macro map, `\myvec` is undefined → fail-soft placeholder (raw command kept in
    // the tooltip, never spilled onto the page). The e-print macro map expands it so it renders.
    const without = html(renderInlineMath('a \\(\\myvec\\) b'));
    expect(without.querySelector('.katex')).toBeNull();
    expect(without.querySelector('[role="img"]')?.getAttribute('title')).toContain('\\myvec');

    const withMacros = html(renderInlineMath('a \\(\\myvec\\) b', { '\\myvec': '\\vec{x}' }));
    expect(withMacros.querySelector('.katex')).not.toBeNull();
    expect(withMacros.textContent).not.toContain('\\myvec');
  });

  it('passes macros through MathDisplay (block formulas)', () => {
    const without = html(<MathDisplay latex={'\\myop'} />);
    expect(without.querySelector('.katex')).toBeNull();
    expect(without.querySelector('[role="img"]')?.getAttribute('title')).toContain('\\myop');

    const c = html(<MathDisplay latex={'\\myop'} macros={{ '\\myop': '\\oplus' }} />);
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('\\myop');
  });

  it('resolves common blackboard-bold fallbacks (\\R) without any meta.macros', () => {
    // \R is not a KaTeX builtin; without the fallback map it would render as red source text.
    const c = html(<MathDisplay latex={'x \\in \\R'} />);
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('\\R');
    expect(c.querySelector('.katex-error')).toBeNull();
  });

  it('swallows non-math layout macros (\\centering) instead of red-flagging them', () => {
    const c = html(<MathDisplay latex={'\\centering x^2'} />);
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('\\centering');
    expect(c.querySelector('.katex-error')).toBeNull();
  });

  it('lets a paper macro override a fallback default', () => {
    const c = html(<MathDisplay latex={'\\R'} macros={{ '\\R': '\\mathbb{Q}' }} />);
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('\\R');
  });

  it('does not leak a \\gdef across macro-less renders (isolated default macros)', () => {
    // KaTeX mutates the macro object it is given — a \gdef writes a global into it. The default
    // (no meta.macros) path is shared by every abstract; a single mutable object would carry one
    // paper's \gdef into every later render. Each default-path render gets a fresh copy instead.
    html(<MathDisplay latex={'\\gdef\\leaktest{LEAKED}'} />);
    const after = html(<MathDisplay latex={'\\leaktest'} />);
    expect(after.textContent).not.toContain('LEAKED'); // definition must not have leaked
    // Isolated → `\leaktest` is undefined → fail-soft placeholder carrying the raw command in its
    // tooltip (had the \gdef leaked, it would instead render "LEAKED" as real KaTeX).
    expect(after.querySelector('[role="img"]')?.getAttribute('title')).toContain('\\leaktest');
  });
});

describe('physics-package macros (KaTeX has no default → whole-formula placeholder)', () => {
  // Renders to real KaTeX (not the 수식 placeholder) and does not leak the raw command.
  function rendersCleanly(latex: string) {
    const c = html(<MathDisplay latex={latex} />);
    expect(c.querySelector('.katex'), latex).not.toBeNull();
    expect(c.textContent, latex).not.toBe('수식');
    return c;
  }

  it('renders \\quantity by dropping the command (literal delimiters remain)', () => {
    const c = rendersCleanly(String.raw`\quantity(x_{i})_{i\in S}`);
    expect(c.textContent).not.toContain('\\quantity');
  });

  it('renders \\tr and \\rank as operator names', () => {
    rendersCleanly(String.raw`\tr(A^{\top}A)`);
    rendersCleanly(String.raw`\rank(C)=\rank(CC^{\top})`);
  });

  it('rewrites \\matrixquantity[...] to a bracketed matrix, nested brackets intact', () => {
    // The inner `[C]^{-1}` must NOT close the outer matrix early.
    const c = rendersCleanly(String.raw`\matrixquantity[a&b\\ c&[C]^{-1}]`);
    expect(c.querySelector('.mord.text, .base')).not.toBeNull();
  });

  it('rewrites a nested (block) \\matrixquantity', () => {
    rendersCleanly(String.raw`\matrixquantity[\matrixquantity[a&b]\\ c]`);
  });

  it('rewrites \\derivative in both operator and operand forms', () => {
    rendersCleanly(String.raw`\derivative[\alpha]{\boldsymbol{x}}{t}=A`); // order + f + var
    rendersCleanly(String.raw`\derivative[\alpha]{t}`); // order + var (operator form)
    rendersCleanly(String.raw`\ker\quantity(\derivative[\alpha]{t})`); // nested in \quantity
  });

  it('renders the broader physics set (operators, vector calc, abs/norm, brackets, order)', () => {
    for (const latex of [
      String.raw`\Tr(\rho)`,
      String.raw`\grad f + \curl \vec{F} - \divergence \vec{G} + \laplacian \psi`,
      String.raw`\abs{x} + \norm{v}`,
      String.raw`\comm{A}{B} = -\acomm{B}{A}`,
      String.raw`\order{x^2}`,
      String.raw`\int f \dd x`,
      String.raw`\vb{a}\cdot\vu{n}`,
    ]) {
      rendersCleanly(latex);
    }
  });

  it('rewrites \\pdv (partial) with \\partial, and \\smqty like a matrix', () => {
    const pd = html(<MathDisplay latex={String.raw`\pdv[2]{f}{x}`} />);
    expect(pd.querySelector('.katex')).not.toBeNull();
    expect(pd.textContent).not.toBe('수식');
    rendersCleanly(String.raw`\smqty[a & b \\ c & d]`);
  });

  it('does NOT override KaTeX builtins — \\div stays the division sign', () => {
    // Physics redefines \div as divergence, but overriding it would break every paper using ÷.
    const c = rendersCleanly(String.raw`a \div b`);
    expect(c.textContent).toContain('÷');
  });

  it('leaves an unrecognised \\derivative shape verbatim (fail-soft, no crash)', () => {
    // No operand group → not the expected form; must not throw, degrades to the placeholder.
    const c = html(<MathDisplay latex={String.raw`\derivative`} />);
    expect(c.textContent).toBe('수식');
  });
});

describe('renderRichText (summary fields: markdown + math)', () => {
  it('renders **bold** as <strong>', () => {
    const c = html(renderRichText('훈련 방법 **분류**를 제안'));
    expect(c.querySelector('strong')?.textContent).toBe('분류');
    expect(c.textContent).not.toContain('**');
  });

  it('renders `- ` bullet lines as a <ul><li> list', () => {
    const c = html(renderRichText('- 첫째 항목\n- 둘째 항목'));
    const items = c.querySelectorAll('li');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('첫째 항목');
  });

  it('splits blank-line paragraphs and does not show literal \\n\\n', () => {
    const c = html(renderRichText('첫 문단\\n\\n둘째 문단'));
    expect(c.querySelectorAll('p').length).toBe(2);
    expect(c.textContent).not.toContain('\\n');
  });

  it('renders math inside a bullet item, and preserves LaTeX commands (\\nabla)', () => {
    const c = html(renderRichText('- 힘은 $F=-\\nabla_r E$ 로 산출'));
    expect(c.querySelector('li .katex')).not.toBeNull();
    expect(c.textContent).not.toContain('$F='); // math consumed, not shown raw
  });

  it('combines bold + inline math in one line', () => {
    const c = html(renderRichText('**핵심**: $\\lambda_E=5$'));
    expect(c.querySelector('strong')).not.toBeNull();
    expect(c.querySelector('.katex')).not.toBeNull();
  });
});

describe('renderInlineRich (inline summary fields)', () => {
  it('normalizes a literal \\n into a real break (not shown as text)', () => {
    const c = html(renderInlineRich('첫 줄\\n둘째 줄'));
    expect(c.textContent).not.toContain('\\n');
    expect(c.textContent).toContain('둘째 줄');
  });

  it('preserves LaTeX commands and renders inline math (\\nabla)', () => {
    const c = html(renderInlineRich('기울기 $\\nabla f$ 사용'));
    expect(c.querySelector('.katex')).not.toBeNull();
    expect(c.textContent).not.toContain('$\\nabla');
  });

  it('renders **bold** inline', () => {
    const c = html(renderInlineRich('코드 **공개**'));
    expect(c.querySelector('strong')?.textContent).toBe('공개');
  });
});
