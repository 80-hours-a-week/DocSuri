import { anthropic } from "@ai-sdk/anthropic";
import { streamText, type CoreMessage } from "ai";

// Vercel AI SDK chat endpoint. Phase 0 talks to Anthropic directly; when the
// EKS sprint switches to Bedrock the import becomes
// `@ai-sdk/amazon-bedrock` and the model id changes — no UI changes needed.
export const runtime = "edge";

export async function POST(req: Request) {
  const { messages } = (await req.json()) as { messages: CoreMessage[] };

  const result = await streamText({
    model: anthropic(process.env.LLM_MODEL ?? "claude-haiku-4-5"),
    system:
      "당신은 논문 요약 보조다. 사용자 질문에 한국어(English) 병기 규칙(AGENTS.md §6.2)을 지켜 답한다. " +
      "모든 진술에는 출처가 있다면 [§n.m] 또는 [p.X ¶Y] anchor를 부착한다.",
    messages,
  });

  return result.toDataStreamResponse();
}
