import styles from './PhoneMockupFrame.module.css';

// PhoneMockupFrame (LC-1, NFR-U2, SEC-4) — phone-first full-bleed on phones;
// from tablet up, the app is centered inside a fixed-width phone mockup with NO
// reflow (the inner width is pinned to the phone viewport). Viewport branching
// is purely CSS (media query), so the component tree is identical everywhere.
// frame-ancestors 'self' (middleware) keeps the mockup same-origin.

export function PhoneMockupFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className={styles.stage}>
      <div className={styles.frame} data-testid="phone-mockup-frame">
        {children}
      </div>
    </div>
  );
}
