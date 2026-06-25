'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { applyTheme, readStoredTheme, type Theme } from '@/lib/theme';

// ThemeContext (U10 마이페이지 설정 — 다크모드 수동 전환). 브라우저별 저장(localStorage)만 한다,
// 계정 동기화는 범위 밖. 미설정 시 OS의 prefers-color-scheme을 그대로 따른다(app/globals.css).
// 첫 페인트 전 깜빡임 방지는 `app/layout.tsx`의 인라인 스크립트(`THEME_INIT_SCRIPT`)가 처리하므로,
// 이 Provider는 마운트 시 그 결과를 React state로 읽어오기만 한다(DOM을 다시 쓰지 않음).

interface ThemeValue {
  /** 사용자가 수동으로 고른 테마. `null`이면 OS 설정을 따른다(수동 전환 안 함). */
  theme: Theme | null;
  setTheme: (theme: Theme | null) => void;
}

const ThemeCtx = createContext<ThemeValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme | null>(null);

  useEffect(() => {
    setThemeState(readStoredTheme());
  }, []);

  const setTheme = useCallback((next: Theme | null) => {
    applyTheme(next);
    setThemeState(next);
  }, []);

  const value = useMemo<ThemeValue>(() => ({ theme, setTheme }), [theme, setTheme]);

  return <ThemeCtx.Provider value={value}>{children}</ThemeCtx.Provider>;
}

export function useTheme(): ThemeValue {
  const ctx = useContext(ThemeCtx);
  if (!ctx) throw new Error('useTheme must be used within a ThemeProvider');
  return ctx;
}
