// 검색 상태 ↔ URL 직렬화 (US-DISC-02: "필터 상태는 URL 쿼리에 직렬화 → 새로고침 유지").

import { EMPTY_FILTERS, type SearchFilters, type SortKey } from "./types";

export interface SearchState {
  query: string;
  filters: SearchFilters;
  sortKey: SortKey;
  selectedTerms: string[];
}

export const EMPTY_STATE: SearchState = {
  query: "",
  filters: EMPTY_FILTERS,
  sortKey: "similarity",
  selectedTerms: [],
};

const SORT_KEYS: SortKey[] = ["similarity", "citations", "recency"];

export function stateToParams(state: SearchState): URLSearchParams {
  const p = new URLSearchParams();
  if (state.query) p.set("q", state.query);
  if (state.filters.year_min != null) p.set("ymin", String(state.filters.year_min));
  if (state.filters.year_max != null) p.set("ymax", String(state.filters.year_max));
  if (state.filters.field_tags.length) p.set("tags", state.filters.field_tags.join(","));
  if (state.sortKey !== "similarity") p.set("sort", state.sortKey);
  if (state.selectedTerms.length) p.set("terms", state.selectedTerms.join(","));
  return p;
}

// URLSearchParams / ReadonlyURLSearchParams(useSearchParams 반환) / plain object 모두 허용.
interface GetLike {
  get(key: string): string | null;
}
type ParamLike = GetLike | Record<string, string | string[] | undefined>;

function read(params: ParamLike, key: string): string | undefined {
  if (typeof (params as GetLike).get === "function") {
    return (params as GetLike).get(key) ?? undefined;
  }
  const v = (params as Record<string, string | string[] | undefined>)[key];
  return Array.isArray(v) ? v[0] : v;
}

export function paramsToState(params: ParamLike): SearchState {
  const num = (v: string | undefined) => {
    if (v == null || v === "") return null;
    const n = Number(v);
    return Number.isNaN(n) ? null : n; // ymin=abc 같은 비정상 값은 무시
  };
  const csv = (v: string | undefined) => (v ? v.split(",").filter(Boolean) : []);
  const sortRaw = read(params, "sort") as SortKey | undefined;
  return {
    query: read(params, "q") ?? "",
    filters: {
      year_min: num(read(params, "ymin")),
      year_max: num(read(params, "ymax")),
      field_tags: csv(read(params, "tags")),
    },
    sortKey: sortRaw && SORT_KEYS.includes(sortRaw) ? sortRaw : "similarity",
    selectedTerms: csv(read(params, "terms")),
  };
}
