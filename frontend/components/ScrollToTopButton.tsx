'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './ScrollToTopButton.module.css';

// "맨 위로" button for the long reading surfaces (본문 / 본문 번역). It finds its nearest
// scrollable ancestor (the `.page` reading surface — the content scroller on both phone and
// the desktop mockup) and appears once the reader has scrolled past a threshold; tapping it
// smooth-scrolls that container back to the top. Inert (not focusable) while hidden.
const SHOW_AFTER_PX = 320;

export function ScrollToTopButton() {
  const ref = useRef<HTMLButtonElement>(null);
  const scrollerRef = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let el = ref.current?.parentElement ?? null;
    while (el) {
      const overflowY = getComputedStyle(el).overflowY;
      if (overflowY === 'auto' || overflowY === 'scroll') break;
      el = el.parentElement;
    }
    scrollerRef.current = el;
    if (!el) return;
    const onScroll = () => setVisible(el.scrollTop > SHOW_AFTER_PX);
    onScroll();
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
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
