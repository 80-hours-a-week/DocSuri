import {
  BedrockRuntimeClient,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";

const client = new BedrockRuntimeClient({
  region: process.env.AWS_REGION ?? "ap-northeast-2",
});

const EMBED_MODEL = "amazon.titan-embed-text-v2:0";

/**
 * 텍스트 한 건을 Bedrock Titan Embed Text V2로 임베딩.
 * 반환값: 1024차원 number[]
 */
export async function embedText(text: string): Promise<number[]> {
  const cmd = new InvokeModelCommand({
    modelId: EMBED_MODEL,
    contentType: "application/json",
    accept: "application/json",
    body: JSON.stringify({ inputText: text }),
  });

  const res = await client.send(cmd);
  const data = JSON.parse(Buffer.from(res.body).toString("utf-8"));
  return data.embedding as number[];
}

/**
 * 여러 텍스트를 병렬로 임베딩 (concurrency 기본 5).
 */
export async function embedBatch(
  texts: string[],
  concurrency = 5
): Promise<(number[] | null)[]> {
  const results: (number[] | null)[] = new Array(texts.length).fill(null);

  for (let i = 0; i < texts.length; i += concurrency) {
    const chunk = texts.slice(i, i + concurrency);
    const settled = await Promise.allSettled(chunk.map((t) => embedText(t)));

    settled.forEach((r, j) => {
      if (r.status === "fulfilled") {
        results[i + j] = r.value;
      } else {
        console.error(`[embedBatch] index ${i + j} failed:`, r.reason);
      }
    });
  }

  return results;
}
