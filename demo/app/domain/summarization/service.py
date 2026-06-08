"""SummaryService — composition of retriever → prompts → LLM → verify.

Per AGENTS.md:
- §4.1 cache key is owned by `infra/llm`; this module never derives one.
- §4.3 every sentence goes through `crosscutting/verifier`.
- §4.4 every sentence carries an Anchor; missing inline `[§…]` defaults
  to `[§abstract]` (Sprint 1 walking-skeleton fallback).
- §6.5 the public result follows the structured-output schema.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from pydantic import BaseModel

from app.crosscutting.anchor.validator import parse as parse_anchor
from app.crosscutting.glossary.protocol import GlossaryPort
from app.crosscutting.verifier.port import VerifierPort
from app.domain.papers.models import Anchor, GlossaryEntry, Sentence
from app.domain.summarization import prompts, retriever
from app.domain.summarization.presets import AnglePreset, LengthPreset
from app.infra.llm.protocol import LLMPort

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+|(?<=다\.)\s+")

# ```json … ``` or ``` … ``` fences that live Claude wraps §6.5 output in.
_CODE_FENCE = re.compile(r"^\s*```(?:json|JSON)?\s*\n?|\n?\s*```\s*$", re.MULTILINE)


class SummaryResult(BaseModel):
    """§6.5 structured-output shape (the `sentences` half).

    `glossary_additions` is kept for the JSON contract; #02 Sprint 1 does
    not yet propose new terms — #03 translation owns that path.
    """

    sentences: list[Sentence]
    glossary_additions: list[GlossaryEntry] = []
    cache_hit: bool
    latency_ms: int
    model: str


@dataclass
class SummaryStreamSentence:
    sentence: Sentence
    index: int


@dataclass
class SummaryStreamDone:
    glossary_additions: list[GlossaryEntry]
    model: str
    latency_ms: int


@dataclass
class SummaryStreamFailure:
    message: str


SummaryStreamEvent = SummaryStreamSentence | SummaryStreamDone | SummaryStreamFailure


class SummaryService:
    def __init__(
        self,
        llm: LLMPort,
        verifier: VerifierPort,
        glossary: GlossaryPort,
    ) -> None:
        self._llm = llm
        self._verifier = verifier
        self._glossary = glossary

    async def summarize(
        self,
        paper_id: str,
        length: LengthPreset,
        angle: AnglePreset,
        session_id: str = "default",
    ) -> SummaryResult:
        t0 = time.perf_counter()

        paper, structured_md = await retriever.fetch(paper_id)
        glossary_entries = await self._glossary.list_for_session(session_id)

        req = prompts.build(
            paper=paper,
            length=length,
            angle=angle,
            structured_md=structured_md,
            glossary_entries=glossary_entries,
        )
        resp = await self._llm.complete(req)

        # §6.5 prompt demands JSON; live Claude commonly wraps in code fences.
        # Try structured parse first; fall back to plain-text sentence split
        # so mock LLMs (which return prose) keep working.
        structured = _parse_structured_output(resp.text)
        if structured is not None:
            raw_sentences, glossary_additions = structured
        else:
            split = _split_sentences(resp.text)
            split = _trim_to_cap(split, length.char_cap)
            raw_sentences = [{"text": s, "anchor": None} for s in split]
            glossary_additions = []

        result_sentences: list[Sentence] = []
        for item in raw_sentences:
            text = item["text"]
            anchor = _coerce_anchor(item.get("anchor"), text)
            # §4.3 — verifier port labels the sentence even if the producer
            # self-labeled. We never trust the LLM's own label.
            verify = await self._verifier.verify(
                sentence=text,
                evidence_spans=[structured_md] if structured_md else [],
            )
            result_sentences.append(
                Sentence(
                    text=text,
                    anchor=anchor,
                    verify_label=verify.label,
                    confidence=verify.confidence,
                )
            )

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return SummaryResult(
            sentences=result_sentences,
            glossary_additions=glossary_additions,
            cache_hit=resp.cache_hit,
            latency_ms=latency_ms,
            model=resp.model,
        )


    async def summarize_stream(
        self,
        paper_id: str,
        length: LengthPreset,
        angle: AnglePreset,
        session_id: str = "default",
        section_id: str | None = None,
    ) -> AsyncIterator[SummaryStreamEvent]:
        """NDJSON-streamed summary.

        Asks the LLM for one JSON object per line; each completed line is
        verified (via the §4.3 port) and emitted as a `SummaryStreamSentence`.
        A terminal `SummaryStreamDone` carries the glossary additions and
        cumulative latency. The API layer maps these into SSE frames.

        When ``section_id`` is set, the LLM only sees that section's text —
        the result is a section-scoped summary the user can pin to one
        part of the paper.

        Falls back gracefully if the LLM disregards the NDJSON instruction:
        any non-JSON tail is split on sentence boundaries at flush time so
        the user still sees content rather than nothing.
        """
        t0 = time.perf_counter()
        paper, structured_md = await retriever.fetch(paper_id, section_id=section_id)
        glossary_entries = await self._glossary.list_for_session(session_id)
        req = prompts.build(
            paper=paper,
            length=length,
            angle=angle,
            structured_md=structured_md,
            glossary_entries=glossary_entries,
        )

        emitted_count = 0
        glossary_additions: list[GlossaryEntry] = []
        evidence = [structured_md] if structured_md else []
        buffer = ""
        model_label = "unknown"

        async def emit_sentence(text: str, anchor_raw: object) -> SummaryStreamSentence:
            nonlocal emitted_count
            anchor = _coerce_anchor(anchor_raw, text)
            verify = await self._verifier.verify(sentence=text, evidence_spans=evidence)
            s = Sentence(
                text=text,
                anchor=anchor,
                verify_label=verify.label,
                confidence=verify.confidence,
            )
            evt = SummaryStreamSentence(sentence=s, index=emitted_count)
            emitted_count += 1
            return evt

        try:
            async for delta in self._llm.stream(req):
                buffer += delta
                # Process every completed line (newline-terminated).
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    parsed = _parse_ndjson_line(line)
                    if parsed is None:
                        # Treat the line as a free-text sentence so the
                        # demo never goes silent if the LLM strays.
                        yield await emit_sentence(line, None)
                        continue
                    if parsed.get("type") == "sentence" and parsed.get("text"):
                        yield await emit_sentence(parsed["text"], parsed.get("anchor"))
                    elif parsed.get("type") == "done":
                        for a in parsed.get("glossary_additions") or []:
                            entry = _coerce_glossary_entry(a)
                            if entry is not None:
                                glossary_additions.append(entry)
                                await self._glossary.add(session_id, entry)
                    # Any other shape is ignored (forward-compatible).

            # Flush trailing buffer as a final fallback.
            tail = buffer.strip()
            if tail:
                parsed = _parse_ndjson_line(tail)
                if parsed and parsed.get("type") == "sentence" and parsed.get("text"):
                    yield await emit_sentence(parsed["text"], parsed.get("anchor"))
                elif parsed and parsed.get("type") == "done":
                    for a in parsed.get("glossary_additions") or []:
                        entry = _coerce_glossary_entry(a)
                        if entry is not None:
                            glossary_additions.append(entry)
                            await self._glossary.add(session_id, entry)
                elif emitted_count == 0:
                    # Producer never spoke JSON at all; degrade to
                    # sentence-split so something reaches the user.
                    for s in _split_sentences(tail):
                        yield await emit_sentence(s, None)

            # Best-effort model label — only the non-streaming complete()
            # surfaces the model id today. Fine for the demo.
            model_label = (
                "claude-sonnet-4-6"
                if "anthropic" in str(type(self._llm)).lower()
                or "claude" in str(type(self._llm)).lower()
                else "mock-deterministic"
            )

            latency_ms = int((time.perf_counter() - t0) * 1000)
            yield SummaryStreamDone(
                glossary_additions=glossary_additions,
                model=model_label,
                latency_ms=latency_ms,
            )
        except Exception as exc:  # noqa: BLE001 — terminal frame is what matters
            logger.exception("summary stream failed for %s", paper_id)
            yield SummaryStreamFailure(message=str(exc))


def _parse_ndjson_line(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("{"):
        # Some models leak a stray ```json fence even when asked not to.
        line = line.lstrip("`json ").lstrip("`")
    try:
        v = json.loads(line)
        return v if isinstance(v, dict) else None
    except json.JSONDecodeError:
        return None


def _coerce_glossary_entry(value: object) -> GlossaryEntry | None:
    if not isinstance(value, dict):
        return None
    en = value.get("english")
    ko = value.get("korean")
    if not en or not ko:
        return None
    try:
        return GlossaryEntry(english=str(en), korean=str(ko))
    except Exception:  # noqa: BLE001
        return None


def _parse_structured_output(
    text: str,
) -> tuple[list[dict], list[GlossaryEntry]] | None:
    """Try to parse the §6.5 JSON envelope; return None on any failure.

    Live Claude commonly wraps JSON in ```json … ``` fences (with optional
    prose before/after). Mock LLMs return free prose. We try, in order:
    direct parse → fence-stripped → first '{…}' substring. Any success wins.
    """
    if not text:
        return None

    candidates: list[str] = [text.strip()]
    fenceless = _CODE_FENCE.sub("", text).strip()
    if fenceless and fenceless != candidates[0]:
        candidates.append(fenceless)
    # Greedy curly-brace span: handles "Here is the JSON: { … }" wrappers.
    if m := re.search(r"\{.*\}", text, re.DOTALL):
        candidates.append(m.group(0))

    data = None
    for c in candidates:
        try:
            data = json.loads(c)
            break
        except json.JSONDecodeError:
            continue

    # Rescue: response truncated mid-JSON (max_tokens hit). Pull out each
    # complete `"text": "…"` field via regex — we lose anchors / glossary
    # but at least surface readable sentences instead of one raw fence blob.
    if data is None:
        rescued = re.findall(r'"text"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if rescued:
            logger.warning("LLM output truncated; rescued %d sentence(s)", len(rescued))
            return ([{"text": t.replace('\\n', '\n'), "anchor": None} for t in rescued], [])
        return None

    if isinstance(data, list):
        raw = data
        additions_raw: list = []
    elif isinstance(data, dict):
        raw = data.get("sentences") or []
        additions_raw = data.get("glossary_additions") or []
    else:
        return None

    sentences: list[dict] = []
    for entry in raw:
        if isinstance(entry, dict) and "text" in entry:
            sentences.append({"text": str(entry["text"]), "anchor": entry.get("anchor")})
        elif isinstance(entry, str):
            sentences.append({"text": entry, "anchor": None})
    if not sentences:
        return None

    additions: list[GlossaryEntry] = []
    for a in additions_raw:
        if isinstance(a, dict) and a.get("english") and a.get("korean"):
            try:
                additions.append(GlossaryEntry(english=a["english"], korean=a["korean"]))
            except Exception:  # noqa: BLE001 — defensive: drop malformed entries
                logger.debug("dropped malformed glossary_addition: %r", a)
    return sentences, additions


def _coerce_anchor(value: object, fallback_text: str) -> Anchor:
    """Accept Anchor dict, `[§…]` string, or None — always return an Anchor."""
    if isinstance(value, dict):
        try:
            return Anchor.model_validate(value)
        except Exception:  # noqa: BLE001
            pass
    if isinstance(value, str):
        if parsed := parse_anchor(value):
            return parsed
    if parsed := parse_anchor(fallback_text):
        return parsed
    return Anchor(section_id="abstract")


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p.strip()]
    if not parts:
        return [text.strip()] if text.strip() else []
    return parts


def _trim_to_cap(sentences: list[str], cap: int) -> list[str]:
    """Drop trailing sentences once total Korean char count exceeds cap.

    Keep at least one sentence so the result is never empty.
    """

    trimmed: list[str] = []
    total = 0
    for s in sentences:
        if trimmed and total + len(s) > cap:
            break
        trimmed.append(s)
        total += len(s)
    return trimmed or sentences[:1]
