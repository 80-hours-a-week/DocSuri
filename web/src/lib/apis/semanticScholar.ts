import type { NormalizedPaper } from "./types";

const BASE = "https://api.semanticscholar.org/graph/v1/paper/search";
const FIELDS = [
  "title",
  "abstract",
  "openAccessPdf",
  "year",
  "externalIds",
  "citationCount",
  "influentialCitationCount",
  "authors",
].join(",");

export async function fetchSemanticScholar(
  query: string,
  limit = 20
): Promise<NormalizedPaper[]> {
  const url = new URL(BASE);
  url.searchParams.set("query", query);
  url.searchParams.set("fields", FIELDS);
  url.searchParams.set("limit", String(limit));

  const headers: Record<string, string> = {};
  if (process.env.SEMANTIC_SCHOLAR_API_KEY) {
    headers["x-api-key"] = process.env.SEMANTIC_SCHOLAR_API_KEY;
  }

  const res = await fetch(url.toString(), { headers, cache: "no-store" });
  if (!res.ok) throw new Error(`Semantic Scholar fetch failed: ${res.status}`);

  const data = await res.json();

  return (data.data ?? []).map((paper: Record<string, unknown>): NormalizedPaper => {
    const ext = (paper.externalIds ?? {}) as Record<string, string>;
    const authors = (
      (paper.authors as { name: string }[]) ?? []
    ).map((a) => ({ name: a.name ?? "" }));

    const pdfInfo = paper.openAccessPdf as { url?: string } | null;

    return {
      arxiv_id: ext.ArXiv ?? null,
      s2_paper_id: (paper.paperId as string) ?? null,
      doi: ext.DOI ?? null,
      title: (paper.title as string) ?? "",
      authors,
      year: (paper.year as number) ?? null,
      abstract: (paper.abstract as string) ?? null,
      citation_count: (paper.citationCount as number) ?? 0,
      influential_count: (paper.influentialCitationCount as number) ?? 0,
      pdf_url: pdfInfo?.url ?? null,
    };
  });
}
