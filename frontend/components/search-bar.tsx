"use client";

// 검색 폼 — US-DISC-01. 영문·한국어 자연어 입력 허용 (NFR-LANG-02).

import { useState } from "react";
import { Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface SearchBarProps {
  initialQuery: string;
  onSearch: (query: string) => void;
}

export function SearchBar({ initialQuery, onSearch }: SearchBarProps) {
  const [value, setValue] = useState(initialQuery);

  return (
    <form
      role="search"
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        const q = value.trim();
        if (q) onSearch(q);
      }}
    >
      <Input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="연구 의도를 자연어로 입력 (영문·한국어)"
        aria-label="검색어"
        maxLength={500}
        className="h-11"
      />
      <Button type="submit" className="h-11 shrink-0" disabled={!value.trim()}>
        <Search className="size-4" aria-hidden />
        <span className="sr-only sm:not-sr-only">검색</span>
      </Button>
    </form>
  );
}
