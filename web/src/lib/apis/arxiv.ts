import { XMLParser } from "fast-xml-parser";
import type { NormalizedPaper } from "./types";

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "@_",
  isArray: (name) => ["entry", "author", "link", "category"].includes(name),
});

export async function fetchArxiv(
  query: string,
  limit = 20
): Promise<NormalizedPaper[]> {
  const url = new URL("https://export.arxiv.org/api/query");
  url.searchParams.set("search_query", `all:${query}`);
  url.searchParams.set("start", "0");
  url.searchParams.set("max_results", String(limit));
  url.searchParams.set("sortBy", "relevance");

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`arXiv fetch failed: ${res.status}`);

  const xml = await res.text();
  const feed = parser.parse(xml);
  const entries: unknown[] = feed?.feed?.entry ?? [];

  return entries.map((entry): NormalizedPaper => {
    const e = entry as Record<string, unknown>;

    // "http://arxiv.org/abs/1706.03762v5" → "1706.03762"
    const idUrl = (e.id as string) ?? "";
    const arxivId = idUrl.split("/abs/")[1]?.replace(/v\d+$/, "") ?? null;

    // PDF link: <link title="pdf" href="..."/>
    const links = (e.link as Record<string, string>[]) ?? [];
    const pdfLink = links.find((l) => l["@_title"] === "pdf");
    const pdfUrl = pdfLink?.["@_href"] ?? null;

    // Authors
    const rawAuthors = (e.author as Record<string, string>[]) ?? [];
    const authors = rawAuthors.map((a) => ({ name: a.name ?? "" }));

    // Year from published "2017-06-12T..."
    const published = (e.published as string) ?? "";
    const year = published ? parseInt(published.slice(0, 4), 10) : null;

    return {
      arxiv_id: arxivId,
      doi: (e["arxiv:doi"] as string) ?? null,
      title: ((e.title as string) ?? "").replace(/\s+/g, " ").trim(),
      authors,
      year,
      abstract: ((e.summary as string) ?? "").replace(/\s+/g, " ").trim() || null,
      citation_count: 0,
      influential_count: 0,
      pdf_url: pdfUrl,
    };
  });
}
