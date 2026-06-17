// Lightweight observability for core user paths (LC-9, NFR-U5-O1).
//
// Measures latency + error rate of search/login paths via structured logs. No
// external APM in this slice (deferred to Infra). No PII / no tokens logged.

export type PathOutcome = 'ok' | 'error';

interface PathEvent {
  path: string;
  outcome: PathOutcome;
  durationMs: number;
}

function emit(event: PathEvent): void {
  // Structured, greppable line. Swap for an APM sink at Infra stage.
  const line = JSON.stringify({ kind: 'path', ...event, ts: Date.now() });
  if (event.outcome === 'error') console.warn(line);
  else console.info(line);
}

/** Start timing a backend path; call the returned fn with the outcome. */
export function recordPath(path: string): (outcome: PathOutcome) => void {
  const start = Date.now();
  let done = false;
  return (outcome: PathOutcome) => {
    if (done) return;
    done = true;
    emit({ path, outcome, durationMs: Date.now() - start });
  };
}
