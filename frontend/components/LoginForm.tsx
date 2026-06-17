'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import styles from './AuthForm.module.css';
import { getApiClient, UserFacingError } from '@/lib/api';
import { useSession } from './session/SessionContext';
import { validateEmail, validateRequiredPassword } from '@/lib/api/validate';

// LoginForm (LC-1, US-A2, BR-U5-16) — generalized auth errors (credential
// existence not disclosed). On success, refresh the session and return to the
// preserved destination.

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useSession();
  const redirectTo = params.get('redirect') ?? '/search';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    const emailRes = validateEmail(email);
    const pwRes = validateRequiredPassword(password);
    const errs = {
      email: emailRes.ok ? undefined : emailRes.message,
      password: pwRes.ok ? undefined : pwRes.message,
    };
    setFieldErrors(errs);
    if (errs.email || errs.password) return;

    setFormError(null);
    setSubmitting(true);
    try {
      await getApiClient().login({ email: email.trim(), password });
      await refresh();
      router.push(redirectTo);
    } catch (err) {
      setFormError(
        err instanceof UserFacingError ? err.message : '로그인에 실패했습니다. 다시 시도해 주세요.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={onSubmit} data-testid="login-form">
      {params.get('signup') ? (
        <p className={styles.formError} role="status" data-testid="login-signup-notice">
          가입이 완료되었습니다. 로그인해 주세요.
        </p>
      ) : null}
      {formError ? (
        <p className={styles.formError} role="alert" data-testid="login-form-error">
          {formError}
        </p>
      ) : null}
      <div className={styles.field}>
        <label className={styles.label} htmlFor="login-email">
          이메일
        </label>
        <input
          id="login-email"
          className={styles.input}
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          data-testid="login-email"
        />
        {fieldErrors.email ? <p className={styles.fieldError}>{fieldErrors.email}</p> : null}
      </div>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="login-password">
          비밀번호
        </label>
        <input
          id="login-password"
          className={styles.input}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          data-testid="login-password"
        />
        {fieldErrors.password ? <p className={styles.fieldError}>{fieldErrors.password}</p> : null}
      </div>
      <button type="submit" className={styles.submit} disabled={submitting} data-testid="login-submit">
        로그인
      </button>
    </form>
  );
}
