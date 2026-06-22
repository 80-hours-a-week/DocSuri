import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AssetGallery } from '@/components/AssetGallery';

// Uses the mock transport (NEXT_PUBLIC_DOCSURI_REAL_API unset in tests) → assetsResponse.

describe('AssetGallery', () => {
  it('renders the paper figure/table assets from the manifest', async () => {
    render(<AssetGallery paperId="2401.00001" version={1} anchor={null} />);
    const items = await screen.findAllByTestId('asset-item');
    expect(items).toHaveLength(2);
    // Caption rendered as text; image alt uses the caption (escaped by React).
    expect(screen.getByText(/Figure 1/)).toBeTruthy();
    expect(screen.getByText(/Table 1/)).toBeTruthy();
    const imgs = screen.getAllByRole('img');
    expect(imgs.every((img) => img.getAttribute('loading') === 'lazy')).toBe(true);
  });
});
