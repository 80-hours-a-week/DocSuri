import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({
  region: process.env.AWS_REGION ?? "ap-northeast-2",
});

const CHAT_MODEL = "apac.amazon.nova-micro-v1:0";

export interface LibraryPaper {
  title: string;
  year: number | null;
  abstract: string | null;
}

export interface CandidatePaper {
  id: number;
  title: string;
  year: number | null;
  abstract: string | null;
  citation_count: number;
  similarity_score?: number;
}

export interface RecommendResult {
  rankedIds: number[];       // 추천 순서대로 정렬된 paper id 목록
  reason: string;            // AI 추천 이유 한 줄 요약
}

/**
 * Nova Micro에게 논문 추천 순서를 결정하게 한다.
 *
 * @param library  유저가 저장한 논문 목록 (빈 배열 가능)
 * @param candidates  후보 논문 목록 (최대 30건)
 */
export async function rankPapers(
  library: LibraryPaper[],
  candidates: CandidatePaper[]
): Promise<RecommendResult> {
  const hasLibrary = library.length > 0;

  const librarySection = hasLibrary
    ? `## 사용자가 저장한 논문 (관심 분야 참고)\n` +
      library
        .map((p, i) => `${i + 1}. "${p.title}" (${p.year ?? "연도 미상"})`)
        .join("\n")
    : `## 사용자 라이브러리\n(비어 있음 — 인기도와 최신성 기준으로 추천)`;

  const candidateSection =
    `## 후보 논문 목록\n` +
    candidates
      .map(
        (p) =>
          `[ID:${p.id}] "${p.title}" | ${p.year ?? "?"} | 인용수:${p.citation_count}` +
          (p.similarity_score !== undefined
            ? ` | 유사도:${p.similarity_score.toFixed(3)}`
            : "")
      )
      .join("\n");

  const instruction = hasLibrary
    ? "위 사용자의 관심 논문과 가장 유사하고 관련성 높은 후보 논문을 순서대로 추천하세요."
    : "사용자 라이브러리가 비어 있으므로, 인용수와 최신성을 종합적으로 고려하여 후보 논문을 순서대로 추천하세요.";

  const prompt = `당신은 논문 추천 AI입니다. 다음 정보를 바탕으로 논문을 추천합니다.

${librarySection}

${candidateSection}

## 지시사항
${instruction}

## 응답 형식 (JSON만 출력, 다른 텍스트 없이)
{
  "rankedIds": [id1, id2, id3, ...],
  "reason": "추천 기준 한 줄 요약 (한국어)"
}`;

  const body = {
    messages: [{ role: "user", content: [{ text: prompt }] }],
    inferenceConfig: { maxTokens: 1024, temperature: 0.3 },
  };

  const cmd = new InvokeModelCommand({
    modelId: CHAT_MODEL,
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify(body),
  });

  const res = await client.send(cmd);
  const raw = JSON.parse(Buffer.from(res.body).toString("utf-8"));
  const text: string = raw.output?.message?.content?.[0]?.text ?? "";

  // JSON 파싱 — 마크다운 코드블록 감싸진 경우 처리
  const jsonMatch = text.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error(`LLM이 유효한 JSON을 반환하지 않았습니다: ${text}`);
  }
  const parsed = JSON.parse(jsonMatch[0]) as RecommendResult;
  return parsed;
}
