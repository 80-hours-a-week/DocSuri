'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './ScrollToTopButton.module.css';

// "맨 위로" button for the long reading surfaces (본문 / 본문 번역). The reading content scrolls
// inside a nested container (`.page` on mobile, possibly the phone frame on desktop), so rather
// than guess which element scrolls we listen for scroll events on `document` in the CAPTURE
// phase — that catches a scroll on ANY element (scroll events don't bubble) — and learn the
// active scroller from the event. The button appears once scrolled past a threshold and
// smooth-scrolls that container back to the top. Inert (not focusable) while hidden.
const SHOW_AFTER_PX = 280;

export function ScrollToTopButton() {
  const ref = useRef<HTMLButtonElement>(null);
  const scrollerRef = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Seed a click target from the nearest scrollable ancestor (before any scroll happens).
    let el = ref.current?.parentElement ?? null;
    while (el) {
      const oy = getComputedStyle(el).overflowY;
      if ((oy === 'auto' || oy === 'scroll') && el.scrollHeight > el.clientHeight) break;
      el = el.parentElement;
    }
    scrollerRef.current = el;

    const onScroll = (e: Event) => {
      const target = e.target;
      const scroller =
        target instanceof HTMLElement
          ? target
          : (document.scrollingElement as HTMLElement | null);
      if (!scroller) return;
      scrollerRef.current = scroller; // remember the element actually being scrolled
      setVisible(scroller.scrollTop > SHOW_AFTER_PX);
    };
    document.addEventListener('scroll', onScroll, { capture: true, passive: true });
    return () => document.removeEventListener('scroll', onScroll, { capture: true });
  }, []);

  return (
    <button
      ref={ref}
      type="button"
      className={visible ? `${styles.btn} ${styles.visible}` : styles.btn}
      onClick={() => scrollerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
      aria-label="맨 위로"
      aria-hidden={!visible}
      tabIndex={visible ? 0 : -1}
    >
      ↑
    </button>
  );
}
