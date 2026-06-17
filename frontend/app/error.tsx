'use client';

import { StateView } from '@/components/StateView';

// Root segment error boundary (LC-5, BR-U5-11, SEC-15) — fail-closed: a
// generalized message only, never the error detail / stack.
export default function RootError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div style={{ flex: 1, display: 'flex' }}>
      <StateView kind="error" onRetry={reset} />
    </div>
  );
}
