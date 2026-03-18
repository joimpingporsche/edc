from __future__ import annotations

import re
from typing import Any, Dict, List


MARKER_LINES = {
	"[SECTION_START]",
	"[SECTION_END]",
	"[TABLE_JSON_START]",
	"[TABLE_JSON_END]",
}


def _normalize_text(text: str) -> str:
	text = text.replace("\r\n", "\n").replace("\r", "\n")
	lines = []
	for line in text.split("\n"):
		stripped = line.strip()
		if not stripped:
			continue
		if stripped in MARKER_LINES:
			continue
		lines.append(stripped)
	return "\n".join(lines)


def _split_sentences(text: str) -> List[str]:
	text = re.sub(r"\s+", " ", text).strip()
	if not text:
		return []
	return [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", text) if s.strip()]


def _chunk_by_sentences(
	sentences: List[str],
	window_sentences: int,
	overlap_sentences: int,
) -> List[Dict[str, Any]]:
	chunks = []
	if not sentences:
		return chunks

	step = max(1, window_sentences - overlap_sentences)
	chunk_index = 0
	start = 0

	while start < len(sentences):
		end = min(len(sentences), start + window_sentences)
		chunk_text = " ".join(sentences[start:end]).strip()
		if chunk_text:
			chunks.append(
				{
					"chunk_local_index": chunk_index,
					"text": chunk_text,
					"source_span": {
						"start_sentence": start,
						"end_sentence_exclusive": end,
					},
				}
			)
			chunk_index += 1
		start += step

	return chunks


def _chunk_by_chars(text: str, window_chars: int, overlap_chars: int) -> List[Dict[str, Any]]:
	chunks = []
	if not text:
		return chunks

	step = max(1, window_chars - overlap_chars)
	chunk_index = 0
	start = 0

	while start < len(text):
		end = min(len(text), start + window_chars)
		chunk_text = text[start:end].strip()
		if chunk_text:
			chunks.append(
				{
					"chunk_local_index": chunk_index,
					"text": chunk_text,
					"source_span": {
						"start_char": start,
						"end_char": end,
					},
				}
			)
			chunk_index += 1
		start += step

	return chunks


def chunk_document(
	doc_id: str,
	text: str,
	mode: str = "sentence",
	window_sentences: int = 4,
	overlap_sentences: int = 1,
	window_chars: int = 1800,
	overlap_chars: int = 300,
) -> List[Dict[str, Any]]:
	"""
	Baseline fixed-window chunking.
	This function intentionally avoids section/title/bullet semantics.
	"""
	normalized = _normalize_text(text)

	if mode == "char":
		raw_chunks = _chunk_by_chars(
			normalized,
			window_chars=window_chars,
			overlap_chars=overlap_chars,
		)
	else:
		sentences = _split_sentences(normalized)
		raw_chunks = _chunk_by_sentences(
			sentences,
			window_sentences=window_sentences,
			overlap_sentences=overlap_sentences,
		)

	result = []
	for raw in raw_chunks:
		local_idx = raw["chunk_local_index"]
		result.append(
			{
				"doc_id": doc_id,
				"chunk_id": f"{doc_id}::chunk_{local_idx:05d}",
				"section_id": None,
				"section_title": "",
				"chunk_type": "window_text",
				"text_for_edc": raw["text"],
				"source_span": raw["source_span"],
				"meta": {
					"chunking_variant": "baseline_fixed_window",
					"mode": mode,
				},
			}
		)

	return result
