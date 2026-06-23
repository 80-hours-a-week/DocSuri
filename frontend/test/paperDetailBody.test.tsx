import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PaperDetailIsland } from '@/components/PaperDetailIsland';

// The doc-model body opens in its OWN window (the 본문 route), not inline — so the detail
// page shows a 본문 link (new tab) and no longer mounts the figure/table gallery or an
// inline viewer.
describe('PaperDetailIsland — body opens in a new window', () => {
  it('renders a 본문 link to the doc-model route (new tab), not an inline viewer/gallery', () => {
    render(<PaperDetailIsland paperId="2401.00001" version={1} />);

    const bodyLink = screen.getByTestId('open-doc-model');
    expect(bodyLink.getAttribute('href')).toBe('/paper/2401.00001/doc-model?version=1');
    expect(bodyLink.getAttribute('target')).toBe('_blank');
    expect(bodyLink.getAttribute('rel')).toContain('noopener');

    // 본문 번역 also opens in its own window (not a modal).
    const transLink = screen.getByTestId('open-full-translation');
    expect(transLink.getAttribute('href')).toBe('/paper/2401.00001/translate?version=1');
    expect(transLink.getAttribute('target')).toBe('_blank');

    // No inline rich view and no standalone figure/table gallery on the detail page.
    expect(screen.queryByTestId('docmodel-viewer')).toBeNull();
    expect(screen.queryByTestId('asset-item')).toBeNull();
  });
});
