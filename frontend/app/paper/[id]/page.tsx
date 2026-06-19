import styles from '../../page.module.css';
import header from './paper.module.css';
import { RouteGuard } from '@/components/RouteGuard';
import { AppHeader } from '@/components/AppHeader';
import { PaperDetailIsland } from '@/components/PaperDetailIsland';

// Paper detail route /paper/[id] (Q1=A) — SSR shell (header + arXiv link-out) +
// client island (summary/translation/full-text viewer). protected (RouteGuard).
//
// paperId = arxivId, version = 1 (Q8=A). The arXiv link is derived from the id.
// FLAG: title/authors/abstract on direct navigation need a backend paper-metadata
// endpoint (none yet) — v1 shows arXiv id + link only; metadata is a follow-up.
export default async function PaperPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const arxivUrl = `https://arxiv.org/abs/${encodeURIComponent(id)}`;

  return (
    <RouteGuard redirectTo={`/paper/${id}`}>
      <div className={styles.screen}>
        <AppHeader title="DocSuri" />
        <main className={header.main}>
          <header className={header.head}>
            <p className={header.id}>arXiv:{id}</p>
            <a className={header.link} href={arxivUrl} target="_blank" rel="noopener noreferrer">
              arXiv에서 원문 보기
            </a>
          </header>
          <PaperDetailIsland paperId={id} version={1} arxivUrl={arxivUrl} />
        </main>
      </div>
    </RouteGuard>
  );
}
