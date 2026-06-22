import styles from '../../page.module.css';
import header from './paper.module.css';
import { RouteGuard } from '@/components/RouteGuard';
import { AppHeader } from '@/components/AppHeader';
import { BottomNav } from '@/components/BottomNav';
import { PaperDetailIsland } from '@/components/PaperDetailIsland';

// Detail route /paper/[id] (Q1=A) — SSR shell (AppHeader) + client island. The
// island owns everything below the DocSuri header: the 요약/초록번역/전문번역 action
// bar, metadata, and the full-text body. protected (RouteGuard).
//
// paperId = arxivId, version = 1 (Q8=A). NOTE: title/authors/abstract come from a
// PROVISIONAL paper-metadata endpoint (mock in dev) — see usePaperMeta.
export default async function PaperPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const arxivUrl = `https://arxiv.org/abs/${encodeURIComponent(id)}`;

  return (
    <RouteGuard redirectTo={`/paper/${id}`}>
      <div className={styles.screen}>
        <AppHeader title="DocSuri" />
        <main className={header.main}>
          <PaperDetailIsland paperId={id} version={1} arxivUrl={arxivUrl} />
        </main>
        <BottomNav />
      </div>
    </RouteGuard>
  );
}
