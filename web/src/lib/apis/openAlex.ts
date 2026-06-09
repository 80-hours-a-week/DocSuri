import type { NormalizedPaper } from "./types";

const BASE = "https://api.openalex.org/works";
const SELECT = [
  "id",
  "title",
  "abstract_inverted_index",
  "open_access",
  "primary_location",
  "authorships",
  "publication_year",
  "cited_by_count",
  "ids",
].join(",");

/** 역인덱스 → 원문 텍스트 복원 */
function reconstructAbstract(
  invertedIndex: Record<string, number[]> | null
): string | null {
  if (!invertedIndex) return null;
  const words: string[] = [];
  for (const [word, positions] of Object.entries(invertedIndex)) {
    for (const pos of positions) {
      words[pos] = word;
    }
  }
  return words.filter(Boolean).join(" ") || null;
}

export async function fetchOpenAlex(
  query: string,
  limit = 20
): Promise<NormalizedPaper[]> {
  const url = new URL(BASE);
  url.searchParams.set("search", query);
  url.searchParams.set("select", SELECT);
  url.searchParams.set("per_page", String(limit));
  if (process.env.OPENALEX_EMAIL) {
    url.searchParams.set("mailto", process.env.OPENALEX_EMAIL);
  }

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`OpenAlex fetch failed: ${res.status}`);

  const data = await res.json();

  return (data.results ?? []).map((work: Record<string, unknown>): NormalizedPaper => {
    // "https://openalex.org/W2741809807" → "W2741809807"
    const openalexId = (work.id as string)?.split("/").pop() ?? null;

    const ids = (work.ids ?? {}) as Record<string, string>;
    const doi = ids.doi?.replace("https://doi.org/", "") ?? null;

    const loc = (work.primary_location ?? {}) as Record<string, unknown>;
    const oa = (work.open_access ?? {}) as Record<string, unknown>;
    const pdfUrl =
      (loc.pdf_url as string) ?? (oa.oa_url as string) ?? null;

    const authors = (
      (work.authorships as { author: { display_name?: string } }[]) ?? []
    ).map((a) => ({ name: a.author?.display_name ?? "" }));

    return {
      openalex_id: openalexId,
      doi,
      title: (work.title as string) ?? "",
      authors,
      year: (work.publication_year as number) ?? null,
      abstract: reconstructAbstract(
        (work.abstract_inverted_index as Record<string, number[]>) ?? null
      ),
      citation_count: (work.cited_by_count as number) ?? 0,
      influential_count: 0,
      pdf_url: pdfUrl,
    };
  });
}
