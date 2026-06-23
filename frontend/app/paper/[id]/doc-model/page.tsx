import page from '../reading.module.css';
import { DocModelViewer } from '@/components/DocModelViewer';
import type { AnchorVM } from '@/types/generated';

// Doc-model rich-view route /paper/[id]/doc-model (D4, FD §2.10) — opened in its own window
// from the detail page's 본문 action. A clean reading surface: NO app header / bottom nav and
// NO client RouteGuard (auth + OA license are enforced by the backend getDocModel call; an
// anonymous/ungated request surfaces the unavailable state rather than redirecting). A summary
// source anchor is carried via ?anchorLabel (and optional ?anchorSpan) so the window opens
// scrolled to the matching block. version defaults to 1 (Q8=A).
export default async function DocModelPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const version = Number(Array.isArray(sp.version) ? sp.version[0] : sp.version) || 1;
  const arxivUrl = `https://arxiv.org/abs/${encodeURIComponent(id)}`;

  const label = typeof sp.anchorLabel === 'string' ? sp.anchorLabel : undefined;
  const span = typeof sp.anchorSpan === 'string' ? sp.anchorSpan : '';
  const anchor: AnchorVM | null = label ? { field: '', target: 'section', span, label } : null;

  return (
    <main className={page.page}>
      <DocModelViewer paperId={id} version={version} anchor={anchor} arxivUrl={arxivUrl} />
    </main>
  );
}
