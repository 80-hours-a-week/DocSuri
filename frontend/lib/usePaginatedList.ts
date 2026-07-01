'use client';

import { useCallback, useEffect, useState } from 'react';
import { UserFacingError } from '@/lib/api';

// usePaginatedList (BR-U5, NFR-U5) — cursor-based list state shared by the
// library/saved/history screens. NEVER assumes offset/total count; "더 보기"
// appends the next cursor page. Loading/empty/error are the caller's to render.

export interface Page<T> {
  items: T[];
  nextCursor?: string;
}

export type ListStatus = 'loading' | 'ready' | 'loadingMore' | 'error';

export interface PaginatedList<T> {
  items: T[];
  status: ListStatus;
  error: string | null;
  hasMore: boolean;
  loadMore: () => Promise<void>;
  reload: () => Promise<void>;
  /** Optimistic local removal after a successful server delete. */
  removeLocal: (pred: (item: T) => boolean) => void;
}

export function usePaginatedList<T>(
  fetchPage: (cursor?: string) => Promise<Page<T>>,
): PaginatedList<T> {
  const [items, setItems] = useState<T[]>([]);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [status, setStatus] = useState<ListStatus>('loading');
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setStatus('loading');
    setError(null);
    try {
      const page = await fetchPage(undefined);
      setItems(page.items);
      setCursor(page.nextCursor);
      setStatus('ready');
    } catch (e) {
      setError(e instanceof UserFacingError ? e.message : '목록을 불러오지 못했습니다.');
      setStatus('error');
    }
  }, [fetchPage]);

  const loadMore = useCallback(async () => {
    if (!cursor) return;
    setStatus('loadingMore');
    setError(null);
    try {
      const page = await fetchPage(cursor);
      setItems((prev) => [...prev, ...page.items]);
      setCursor(page.nextCursor);
      setStatus('ready');
    } catch (e) {
      setError(e instanceof UserFacingError ? e.message : '더 불러오지 못했습니다.');
      setStatus('error');
    }
  }, [cursor, fetchPage]);

  const removeLocal = useCallback((pred: (item: T) => boolean) => {
    setItems((prev) => prev.filter((it) => !pred(it)));
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { items, status, error, hasMore: Boolean(cursor), loadMore, reload, removeLocal };
}
