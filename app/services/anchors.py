from __future__ import annotations

import re

from app.models import PaperDocument, Verification

ANCHOR_RE = re.compile(r"\[(§\d+(?:\.\d+)?|p\.\d+\s*¶\d+)\]")
SENTENCE_RE = re.compile(r"(?<=[.!?。！？])\s+")


def anchors_in_text(text: str) -> list[str]:
    return ANCHOR_RE.findall(text)


def known_anchors(paper: PaperDocument) -> set[str]:
    anchors = set(anchors_in_text(paper.text))
    anchors.update(chunk.anchor for chunk in paper.chunks if chunk.anchor)
    return anchors


def evidence_for_anchor(paper: PaperDocument, anchor: str) -> str | None:
    for chunk in paper.chunks:
        if chunk.anchor == anchor:
            return chunk.text
    escaped = re.escape(f"[{anchor}]")
    match = re.search(rf"{escaped}\s*(.*?)(?=\n\n\[§|\Z)", paper.text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def verify_sentence(sentence: str, paper: PaperDocument) -> Verification:
    anchors = anchors_in_text(sentence)
    if not anchors:
        return Verification(label="NOT_FOUND", rationale="문장에 anchor가 없다.")

    available = known_anchors(paper)
    missing = [anchor for anchor in anchors if anchor not in available]
    if missing:
        return Verification(label="NOT_FOUND", rationale=f"존재하지 않는 anchor: {', '.join(missing)}")

    evidence_parts = [evidence_for_anchor(paper, anchor) or "" for anchor in anchors]
    if any(part.strip() for part in evidence_parts):
        return Verification(label="SUPPORTED", rationale="anchor가 원문 span과 매칭된다.")

    evidence = " ".join(evidence_parts).lower()
    sentence_terms = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z-]{4,}", sentence)
        if token.lower() not in {"therefore", "however", "because"}
    }
    overlap = [token for token in sentence_terms if token in evidence]
    if sentence_terms and not overlap:
        return Verification(label="PARTIALLY_SUPPORTED", rationale="anchor는 존재하지만 원문 어휘 근거가 약하다.")
    return Verification(label="SUPPORTED", rationale="anchor가 원문 span과 매칭된다.")


def split_sentences(text: str) -> list[str]:
    return [sentence.strip() for sentence in SENTENCE_RE.split(text.strip()) if sentence.strip()]
