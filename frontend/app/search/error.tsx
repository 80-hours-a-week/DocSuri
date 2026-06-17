'use client';

import { StateView } from '@/components/StateView';

// Search segment error boundary (LC-5) — isolates a search-route failure from
// the rest of the shell. Fail-closed generalized message (SEC-15).
export default function SearchError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div style={{ flex: 1, display: 'flex', padding: 16 }}>
      <StateView kind="error" onRetry={reset} />
    </div>
  );
}
