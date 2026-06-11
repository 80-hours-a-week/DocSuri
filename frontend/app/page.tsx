// 검색 페이지(Server Component). searchParams로 초기 상태를 읽고, 쿼리가 있으면
// 서버에서 1차 검색해 결과를 SSR로 내려준다 → 새로고침 시 URL 상태·결과 복원(US-DISC-02).

import { SearchExperience } from "@/components/search-experience";
import { stateToRequest } from "@/lib/api";
import { performSearch } from "@/lib/search-service";
import type { SearchResponse } from "@/lib/types";
import { paramsToState } from "@/lib/url-state";

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const initialState = paramsToState(await searchParams);
  let initialResponse: SearchResponse | null = null;
  if (initialState.query.trim()) {
    try {
      initialResponse = await performSearch(stateToRequest(initialState));
    } catch {
      // 백엔드 오류 시 빈 상태로 SSR — 클라이언트가 재검색해 오류를 표면화한다.
      initialResponse = null;
    }
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-6 sm:py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">DocSuri · Discover</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          연구 의도를 자연어(영문·한국어)로 입력하면 의미 유사도로 논문을 찾아 줍니다.
        </p>
      </header>
      <SearchExperience initialState={initialState} initialResponse={initialResponse} />
    </main>
  );
}
