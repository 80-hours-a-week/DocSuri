import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-6 py-16">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">DocSuri</h1>
        <p className="mt-2 text-neutral-600">
          AI 연구·실무자가 논문 흐름에서 자기 연구에 필요한 신호만 빠르게 골라내는 소비 도구.
        </p>
      </header>

      <section className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Sprint 1 — Walking skeleton</h2>
        <ul className="mt-3 space-y-1 text-sm text-neutral-700">
          <li>• #01a 검색 · #01b 인입</li>
          <li>• #02 요약 · #03 번역</li>
        </ul>
        <div className="mt-4 flex gap-3">
          <Link
            href="/chat"
            className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            요약 데모 열기
          </Link>
          <a
            href="/api/auth/signin"
            className="rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
          >
            로그인 (Kakao · Google)
          </a>
        </div>
      </section>
    </main>
  );
}
