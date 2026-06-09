"use client";

import { useChat } from "ai/react";

export default function ChatPage() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "/api/chat",
  });

  return (
    <main className="mx-auto flex h-screen max-w-3xl flex-col px-6 py-8">
      <header className="mb-4">
        <h1 className="text-xl font-semibold">요약 데모 (Sprint 1)</h1>
        <p className="text-sm text-neutral-500">
          AGENTS.md §6.1 anchor · §6.2 glossing 규칙을 따르는 응답 스트리밍.
        </p>
      </header>

      <ol className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-neutral-200 bg-white p-4 text-sm">
        {messages.map((m) => (
          <li key={m.id} className="flex gap-2">
            <span className="w-12 shrink-0 text-neutral-500">
              {m.role === "user" ? "나" : "AI"}
            </span>
            <span className="whitespace-pre-wrap">{m.content}</span>
          </li>
        ))}
      </ol>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="논문 제목 또는 arXiv id…"
          className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          전송
        </button>
      </form>
    </main>
  );
}
