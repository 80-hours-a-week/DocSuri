"use client";

// 정렬·필터 — US-DISC-02. 데스크톱 인라인 / 모바일 단일 액션바 + Drawer(바텀시트, ≤2탭, NFR-MOBILE-04).
// 상태는 상위가 보유하고 URL로 직렬화한다(새로고침 유지).

import { SlidersHorizontal } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SearchFilters, SortKey } from "@/lib/types";

const YEARS = [2026, 2025, 2024, 2023];
const TAGS = [
  { id: "cs.LG", label: "머신러닝 (cs.LG)" },
  { id: "cs.CL", label: "NLP (cs.CL)" },
  { id: "cs.CV", label: "비전 (cs.CV)" },
  { id: "cs.AI", label: "AI (cs.AI)" },
  { id: "cs.IR", label: "정보검색 (cs.IR)" },
];
const SORT_LABEL: Record<SortKey, string> = {
  similarity: "유사도순",
  citations: "인용수순",
  recency: "최신순",
};
const ALL = "all";

interface FilterSortBarProps {
  filters: SearchFilters;
  sortKey: SortKey;
  onFiltersChange: (next: SearchFilters) => void;
  onSortChange: (next: SortKey) => void;
}

function YearSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      <Select
        value={value != null ? String(value) : ALL}
        onValueChange={(v) => onChange(v === ALL ? null : Number(v))}
      >
        <SelectTrigger className="h-11 min-w-28">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>전체</SelectItem>
          {YEARS.map((y) => (
            <SelectItem key={y} value={String(y)}>
              {y}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function FilterControls({ filters, onFiltersChange }: Pick<FilterSortBarProps, "filters" | "onFiltersChange">) {
  const toggleTag = (id: string) => {
    const has = filters.field_tags.includes(id);
    onFiltersChange({
      ...filters,
      field_tags: has ? filters.field_tags.filter((t) => t !== id) : [...filters.field_tags, id],
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <YearSelect
          label="시작 연도"
          value={filters.year_min}
          onChange={(v) => onFiltersChange({ ...filters, year_min: v })}
        />
        <YearSelect
          label="종료 연도"
          value={filters.year_max}
          onChange={(v) => onFiltersChange({ ...filters, year_max: v })}
        />
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">분야</Label>
        <div className="flex flex-wrap gap-2">
          {TAGS.map((t) => {
            const active = filters.field_tags.includes(t.id);
            return (
              <button
                key={t.id}
                type="button"
                role="switch"
                aria-checked={active}
                onClick={() => toggleTag(t.id)}
                className={`inline-flex min-h-9 items-center rounded-full border px-3 py-1 text-sm transition-colors ${
                  active
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-input bg-background hover:bg-accent"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SortSelect({ sortKey, onSortChange }: Pick<FilterSortBarProps, "sortKey" | "onSortChange">) {
  return (
    <Select value={sortKey} onValueChange={(v) => onSortChange(v as SortKey)}>
      <SelectTrigger className="h-11 min-w-32" aria-label="정렬 기준">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {(Object.keys(SORT_LABEL) as SortKey[]).map((k) => (
          <SelectItem key={k} value={k}>
            {SORT_LABEL[k]}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function FilterSortBar({ filters, sortKey, onFiltersChange, onSortChange }: FilterSortBarProps) {
  const activeCount =
    (filters.year_min != null ? 1 : 0) + (filters.year_max != null ? 1 : 0) + filters.field_tags.length;

  return (
    <div className="space-y-3">
      {/* 액션바 — 정렬은 항상 노출 / 모바일은 필터 Drawer 버튼 */}
      <div className="flex items-center gap-2">
        <SortSelect sortKey={sortKey} onSortChange={onSortChange} />

        <Drawer>
          <DrawerTrigger asChild>
            <Button variant="outline" className="h-11 md:hidden">
              <SlidersHorizontal className="size-4" aria-hidden />
              필터
              {activeCount > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {activeCount}
                </Badge>
              )}
            </Button>
          </DrawerTrigger>
          <DrawerContent>
            <DrawerHeader>
              <DrawerTitle>필터</DrawerTitle>
            </DrawerHeader>
            <div className="px-4 pb-6">
              <FilterControls filters={filters} onFiltersChange={onFiltersChange} />
              <DrawerClose asChild>
                <Button className="mt-5 h-11 w-full">적용</Button>
              </DrawerClose>
            </div>
          </DrawerContent>
        </Drawer>
      </div>

      {/* 데스크톱 인라인 필터 */}
      <div className="hidden md:block">
        <FilterControls filters={filters} onFiltersChange={onFiltersChange} />
      </div>
    </div>
  );
}
