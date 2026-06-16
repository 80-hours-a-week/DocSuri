'use client';

// Global error boundary (LC-5, SEC-15) — last-resort, replaces the whole shell.
// Fail-closed: generalized copy only.
export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="ko">
      <body style={{ fontFamily: 'system-ui, sans-serif', padding: 40, textAlign: 'center' }}>
        <h1 style={{ fontSize: 18 }}>문제가 발생했습니다</h1>
        <p style={{ color: '#6b7280', fontSize: 14 }}>잠시 후 다시 시도해 주세요.</p>
        <button
          type="button"
          onClick={reset}
          data-testid="global-error-retry"
          style={{ minHeight: 44, padding: '0 20px', marginTop: 12 }}
        >
          다시 시도
        </button>
      </body>
    </html>
  );
}
