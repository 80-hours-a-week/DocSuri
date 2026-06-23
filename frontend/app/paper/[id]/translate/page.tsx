import page from '../reading.module.css';
import { FullTranslationIsland } from '@/components/FullTranslationIsland';

// Full-text translation route /paper/[id]/translate (FR-13, scope=full) — opened in its own
// window from the detail page's 본문 번역 action, mirroring the 본문 (doc-model) window: a clean
// reading surface with NO app header / bottom nav and NO client RouteGuard (auth is enforced
// by the backend summarize call). version defaults to 1 (Q8=A).
export default async function TranslatePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const version = Number(Array.isArray(sp.version) ? sp.version[0] : sp.version) || 1;

  return (
    <main className={page.page}>
      <FullTranslationIsland paperId={id} version={version} />
    </main>
  );
}
