/** 외부 API에서 가져온 논문을 DB upsert 전에 정규화한 형태 */
export interface NormalizedPaper {
  arxiv_id?: string | null;
  s2_paper_id?: string | null;
  openalex_id?: string | null;
  doi?: string | null;
  title: string;
  authors: { name: string }[];
  year?: number | null;
  abstract?: string | null;
  citation_count: number;
  influential_count: number;
  pdf_url?: string | null;
}

/** DB에서 읽어온 논문 (id 포함) */
export interface DBPaper {
  id: number;
  arxiv_id: string | null;
  s2_paper_id: string | null;
  openalex_id: string | null;
  doi: string | null;
  title: string;
  authors: { name: string }[];
  year: number | null;
  abstract: string | null;
  pdf_object_key: string | null;
  citation_count: number;
  influential_count: number;
  similarity_score?: number;
  pdf_url?: string | null;
}
