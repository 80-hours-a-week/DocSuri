import pool from "@/lib/db";
import type { NormalizedPaper } from "@/lib/apis/types";

/**
 * 외부 API에서 가져온 논문을 DB에 upsert.
 * 고유 ID(arxiv_id → s2_paper_id → openalex_id → doi) 순서로 충돌 처리.
 * 고유 ID가 없는 논문은 건너뜀.
 */
export async function upsertPapers(papers: NormalizedPaper[]): Promise<void> {
  for (const p of papers) {
    const conflictCol = p.arxiv_id
      ? "arxiv_id"
      : p.s2_paper_id
      ? "s2_paper_id"
      : p.openalex_id
      ? "openalex_id"
      : p.doi
      ? "doi"
      : null;

    if (!conflictCol) continue; // 고유 ID 없으면 skip

    try {
      await pool.query(
        `INSERT INTO papers
           (arxiv_id, s2_paper_id, openalex_id, doi,
            title, authors, year, abstract,
            citation_count, influential_count, status)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'active')
         ON CONFLICT (${conflictCol}) DO UPDATE SET
           s2_paper_id       = COALESCE(EXCLUDED.s2_paper_id,       papers.s2_paper_id),
           openalex_id       = COALESCE(EXCLUDED.openalex_id,       papers.openalex_id),
           doi               = COALESCE(EXCLUDED.doi,               papers.doi),
           title             = EXCLUDED.title,
           authors           = EXCLUDED.authors,
           year              = COALESCE(EXCLUDED.year,              papers.year),
           abstract          = COALESCE(EXCLUDED.abstract,          papers.abstract),
           citation_count    = GREATEST(EXCLUDED.citation_count,    papers.citation_count),
           influential_count = GREATEST(EXCLUDED.influential_count, papers.influential_count),
           status            = 'active'`,
        [
          p.arxiv_id ?? null,
          p.s2_paper_id ?? null,
          p.openalex_id ?? null,
          p.doi ?? null,
          p.title,
          JSON.stringify(p.authors),
          p.year ?? null,
          p.abstract ?? null,
          p.citation_count,
          p.influential_count,
        ]
      );
    } catch (err) {
      console.error("[upsertPapers] skipping paper:", p.title, err);
    }
  }
}
