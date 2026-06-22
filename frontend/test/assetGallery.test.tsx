import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AssetGallery } from '@/components/AssetGallery';

// Uses the mock transport (NEXT_PUBLIC_DOCSURI_REAL_API unset in tests) → assetsResponse
// (one figure + one table).

describe('AssetGallery', () => {
  it('renders compact figure/table thumbnails from the manifest', async () => {
    render(<AssetGallery paperId="2401.00001" version={1} anchor={null} />);
    const items = await screen.findAllByTestId('asset-item');
    expect(items).toHaveLength(2);
    // Caption rendered as text under each thumbnail.
    expect(screen.getByText(/Figure 1/)).toBeTruthy();
    expect(screen.getByText(/Table 1/)).toBeTruthy();
    // Thumbnails lazy-load so dozens of assets don't fetch up front.
    const thumbs = screen.getAllByTestId('asset-thumb-img');
    expect(thumbs.every((img) => img.getAttribute('loading') === 'lazy')).toBe(true);
  });

  it('opens a lightbox with bounded prev/next when a thumbnail is tapped', async () => {
    const user = userEvent.setup();
    render(<AssetGallery paperId="2401.00001" version={1} anchor={null} />);
    const items = await screen.findAllByTestId('asset-item');

    await user.click(within(items[0]).getByRole('button'));
    const dialog = await screen.findByTestId('asset-lightbox');
    expect(within(dialog).getByTestId('asset-lightbox-counter').textContent).toContain('1 / 2');
    // First asset: prev disabled, next enabled.
    expect(within(dialog).getByTestId('asset-lightbox-prev')).toBeDisabled();
    expect(within(dialog).getByTestId('asset-lightbox-next')).not.toBeDisabled();

    // Navigate to the last asset: next becomes disabled.
    await user.click(within(dialog).getByTestId('asset-lightbox-next'));
    expect(screen.getByTestId('asset-lightbox-counter').textContent).toContain('2 / 2');
    expect(screen.getByTestId('asset-lightbox-next')).toBeDisabled();
    expect(screen.getByTestId('asset-lightbox-prev')).not.toBeDisabled();

    // Close returns to the grid.
    await user.click(screen.getByTestId('asset-lightbox-close'));
    expect(screen.queryByTestId('asset-lightbox')).toBeNull();
  });
});
