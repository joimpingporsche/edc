from __future__ import annotations

import re
from typing import Any, Dict, List


SECTION_START = "[SECTION_START]"
SECTION_END = "[SECTION_END]"
TABLE_START = "[TABLE_JSON_START]"
TABLE_END = "[TABLE_JSON_END]"


def _normalize_newlines(text: str) -> str:
	return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_sentences(text: str) -> List[str]:
	text = re.sub(r"\s+", " ", text).strip()
	if not text:
		return []
	return [s.strip() for s in re.split(r"(?<=[\.\!\?])\s+", text) if s.strip()]


def _is_bullet(line: str) -> bool:
	return bool(re.match(r"^\s*([-*•]|\d+\.)\s+", line))


def _section_prefix(title: str) -> str:
	safe_title = title.strip() if title else "Untitled Section"
	return f"SECTION_TITLE: {safe_title}\nCONTENT:\n"


def _split_groups_by_char_limit(lines: List[str], max_chars: int, overlap_items: int = 1) -> List[List[str]]:
	groups = []
	i = 0
	while i < len(lines):
		current = []
		current_len = 0
		j = i
		while j < len(lines):
			candidate = lines[j]
			add_len = len(candidate) + (1 if current else 0)
			if current and current_len + add_len > max_chars:
				break
			current.append(candidate)
			current_len += add_len
			j += 1

		if current:
			groups.append(current)

		if j >= len(lines):
			break

		i = max(i + 1, j - max(0, overlap_items))
	return groups


def _parse_sections(text: str) -> List[Dict[str, Any]]:
	text = _normalize_newlines(text)
	lines = text.split("\n")

	sections = []
	i = 0
	section_counter = 0

	while i < len(lines):
		if lines[i].strip() != SECTION_START:
			i += 1
			continue

		i += 1
		title = "Untitled Section"
		content_lines = []
		tables = []
		line_offset = i + 1
		in_content = False

		while i < len(lines):
			stripped = lines[i].strip()

			if stripped == SECTION_END:
				break

			if stripped.startswith("TITLE:"):
				parsed_title = stripped[len("TITLE:") :].strip()
				if parsed_title:
					title = parsed_title
				i += 1
				continue

			if stripped == "CONTENT:":
				in_content = True
				i += 1
				continue

			if stripped == TABLE_START:
				i += 1
				table_lines = []
				table_start_line = i + 1
				while i < len(lines) and lines[i].strip() != TABLE_END:
					table_lines.append(lines[i])
					i += 1
				table_text = "\n".join(table_lines).strip()
				if table_text:
					tables.append(
						{
							"table_text": table_text,
							"line_range": {
								"start_line": table_start_line,
								"end_line": i,
							},
						}
					)
				if i < len(lines) and lines[i].strip() == TABLE_END:
					i += 1
				continue

			if in_content and stripped:
				content_lines.append(lines[i])

			i += 1

		sections.append(
			{
				"section_id": f"sec_{section_counter:04d}",
				"title": title,
				"content_lines": content_lines,
				"tables": tables,
				"line_range": {
					"start_line": line_offset,
					"end_line": i,
				},
			}
		)
		section_counter += 1

		while i < len(lines) and lines[i].strip() != SECTION_END:
			i += 1
		if i < len(lines) and lines[i].strip() == SECTION_END:
			i += 1

	# Fallback for unstructured documents.
	if not sections:
		cleaned_lines = [line for line in lines if line.strip()]
		sections = [
			{
				"section_id": "sec_0000",
				"title": "Untitled Section",
				"content_lines": cleaned_lines,
				"tables": [],
				"line_range": {
					"start_line": 1,
					"end_line": len(lines),
				},
			}
		]

	return sections


def _is_text_chunk(chunk: Dict[str, Any]) -> bool:
	return chunk.get("chunk_type") in {"section_bullets", "section_prose"}


def _chunk_len(chunk: Dict[str, Any]) -> int:
	return len((chunk.get("text_for_edc") or "").strip())


def _strip_section_prefix(section_title: str, text: str) -> str:
	prefix = _section_prefix(section_title)
	if text.startswith(prefix):
		return text[len(prefix) :].lstrip()
	return text


def _merge_two_chunks(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
	merged = dict(left)
	left_text = (left.get("text_for_edc") or "").strip()
	right_text = (right.get("text_for_edc") or "").strip()

	# Avoid duplicate SECTION_TITLE prefix when both belong to the same section.
	if left.get("section_id") == right.get("section_id"):
		right_text = _strip_section_prefix(right.get("section_title", ""), right_text)

	if left_text and right_text:
		merged["text_for_edc"] = left_text + "\n" + right_text
	else:
		merged["text_for_edc"] = left_text or right_text

	merged_meta = dict(left.get("meta", {}))
	merged_meta["merged_short_chunk"] = True
	merged["meta"] = merged_meta
	return merged


def _is_low_signal_short_chunk(chunk: Dict[str, Any], min_chunk_chars: int) -> bool:
	if not _is_text_chunk(chunk):
		return False
	if _chunk_len(chunk) >= min_chunk_chars:
		return False

	section_title = (chunk.get("section_title") or "").strip().lower()
	payload = _strip_section_prefix(chunk.get("section_title", ""), chunk.get("text_for_edc", "")).strip().lower()

	low_signal_title = re.search(r"\b(footer|header|caption|metamodel view|title)\b", section_title) is not None
	low_signal_payload = re.search(r"\b(caption|metamodel view)\b", payload) is not None

	return low_signal_title or low_signal_payload


def _merge_short_text_chunks(chunks: List[Dict[str, Any]], min_chunk_chars: int, max_chunk_chars: int) -> List[Dict[str, Any]]:
	if min_chunk_chars <= 0:
		return chunks

	max_merge_chars = max_chunk_chars + max(120, int(0.35 * max_chunk_chars))
	working = list(chunks)

	# Backward pass: try to absorb short chunks into the previous text chunk in the same section.
	merged: List[Dict[str, Any]] = []
	for chunk in working:
		if not _is_text_chunk(chunk) or _chunk_len(chunk) >= min_chunk_chars:
			merged.append(chunk)
			continue

		if merged and _is_text_chunk(merged[-1]):
			prev = merged[-1]
			same_section = prev.get("section_id") == chunk.get("section_id")
			if same_section and (_chunk_len(prev) + _chunk_len(chunk) + 1) <= max_merge_chars:
				merged[-1] = _merge_two_chunks(prev, chunk)
				continue

		merged.append(chunk)

	# Forward pass: merge remaining short chunks into the next text chunk in the same section.
	out: List[Dict[str, Any]] = []
	i = 0
	while i < len(merged):
		current = merged[i]
		if _is_text_chunk(current) and _chunk_len(current) < min_chunk_chars and i + 1 < len(merged):
			next_chunk = merged[i + 1]
			same_section = _is_text_chunk(next_chunk) and current.get("section_id") == next_chunk.get("section_id")
			if same_section and (_chunk_len(current) + _chunk_len(next_chunk) + 1) <= max_merge_chars:
				out.append(_merge_two_chunks(current, next_chunk))
				i += 2
				continue
		out.append(current)
		i += 1

	# Final cleanup: drop low-signal tiny leftovers (e.g., isolated footer captions).
	out = [chunk for chunk in out if not _is_low_signal_short_chunk(chunk, min_chunk_chars)]
	return out


def _reindex_chunk_ids(chunks: List[Dict[str, Any]], doc_id: str) -> List[Dict[str, Any]]:
	reindexed = []
	for idx, chunk in enumerate(chunks):
		updated = dict(chunk)
		updated["chunk_id"] = f"{doc_id}::chunk_{idx:05d}"
		reindexed.append(updated)
	return reindexed


def chunk_document(
	doc_id: str,
	text: str,
	max_chunk_chars: int = 2200,
	min_chunk_chars: int = 120,
	bullet_group_size: int = 6,
	prose_window_sentences: int = 4,
	prose_overlap_sentences: int = 1,
	table_rows_per_chunk: int = 25,
) -> List[Dict[str, Any]]:
	sections = _parse_sections(text)
	chunks: List[Dict[str, Any]] = []
	chunk_counter = 0

	for section in sections:
		section_id = section["section_id"]
		section_title = section["title"]
		content_lines: List[str] = section["content_lines"]
		prefix = _section_prefix(section_title)

		# Tables are always emitted as dedicated chunks.
		for table_idx, table in enumerate(section["tables"]):
			rows = [row for row in table["table_text"].split("\n") if row.strip()]

			if len(rows) <= table_rows_per_chunk:
				chunks.append(
					{
						"doc_id": doc_id,
						"chunk_id": f"{doc_id}::chunk_{chunk_counter:05d}",
						"section_id": section_id,
						"section_title": section_title,
						"chunk_type": "table_json",
						"text_for_edc": prefix + table["table_text"],
						"source_span": table["line_range"],
						"meta": {
							"chunking_variant": "adaptive_section",
							"table_index": table_idx,
							"table_mode": "full_json",
						},
					}
				)
				chunk_counter += 1
			else:
				start = 0
				while start < len(rows):
					end = min(len(rows), start + table_rows_per_chunk)
					row_block = "\n".join(rows[start:end])
					chunks.append(
						{
							"doc_id": doc_id,
							"chunk_id": f"{doc_id}::chunk_{chunk_counter:05d}",
							"section_id": section_id,
							"section_title": section_title,
							"chunk_type": "table_rows",
							"text_for_edc": prefix + row_block,
							"source_span": {
								"row_start": start,
								"row_end_exclusive": end,
							},
							"meta": {
								"chunking_variant": "adaptive_section",
								"table_index": table_idx,
								"table_mode": "row_groups",
							},
						}
					)
					chunk_counter += 1
					start = end

		bullet_lines = [line.strip() for line in content_lines if _is_bullet(line)]
		nonempty_lines = [line.strip() for line in content_lines if line.strip()]
		prose_text = " ".join(nonempty_lines)

		# Bullet-dominant section.
		if len(bullet_lines) > max(0, len(nonempty_lines) - len(bullet_lines)):
			for start in range(0, len(bullet_lines), max(1, bullet_group_size)):
				end = min(len(bullet_lines), start + max(1, bullet_group_size))
				group = bullet_lines[start:end]
				base_text = "\n".join(group)
				chunk_text = prefix + base_text

				if len(chunk_text) <= max_chunk_chars:
					chunks.append(
						{
							"doc_id": doc_id,
							"chunk_id": f"{doc_id}::chunk_{chunk_counter:05d}",
							"section_id": section_id,
							"section_title": section_title,
							"chunk_type": "section_bullets",
							"text_for_edc": chunk_text,
							"source_span": {
								"bullet_start": start,
								"bullet_end_exclusive": end,
							},
							"meta": {
								"chunking_variant": "adaptive_section",
								"mode": "bullet_group",
							},
						}
					)
					chunk_counter += 1
					continue

				split_groups = _split_groups_by_char_limit(
					group,
					max(200, max_chunk_chars - len(prefix)),
					overlap_items=1,
				)
				for subgroup_idx, subgroup in enumerate(split_groups):
					chunks.append(
						{
							"doc_id": doc_id,
							"chunk_id": f"{doc_id}::chunk_{chunk_counter:05d}",
							"section_id": section_id,
							"section_title": section_title,
							"chunk_type": "section_bullets",
							"text_for_edc": prefix + "\n".join(subgroup),
							"source_span": {
								"bullet_start": start,
								"subgroup_index": subgroup_idx,
							},
							"meta": {
								"chunking_variant": "adaptive_section",
								"mode": "bullet_adaptive_split",
							},
						}
					)
					chunk_counter += 1
			continue

		# Prose-dominant section.
		sentences = _split_sentences(prose_text)
		step = max(1, prose_window_sentences - prose_overlap_sentences)
		sent_start = 0
		while sent_start < len(sentences):
			sent_end = min(len(sentences), sent_start + max(1, prose_window_sentences))
			payload = " ".join(sentences[sent_start:sent_end]).strip()
			chunk_text = prefix + payload

			if len(chunk_text) <= max_chunk_chars:
				chunks.append(
					{
						"doc_id": doc_id,
						"chunk_id": f"{doc_id}::chunk_{chunk_counter:05d}",
						"section_id": section_id,
						"section_title": section_title,
						"chunk_type": "section_prose",
						"text_for_edc": chunk_text,
						"source_span": {
							"sentence_start": sent_start,
							"sentence_end_exclusive": sent_end,
						},
						"meta": {
							"chunking_variant": "adaptive_section",
							"mode": "prose_window",
						},
					}
				)
				chunk_counter += 1
			else:
				split_groups = _split_groups_by_char_limit(
					sentences[sent_start:sent_end],
					max(200, max_chunk_chars - len(prefix)),
					overlap_items=1,
				)
				for subgroup_idx, subgroup in enumerate(split_groups):
					chunks.append(
						{
							"doc_id": doc_id,
							"chunk_id": f"{doc_id}::chunk_{chunk_counter:05d}",
							"section_id": section_id,
							"section_title": section_title,
							"chunk_type": "section_prose",
							"text_for_edc": prefix + " ".join(subgroup),
							"source_span": {
								"sentence_start": sent_start,
								"subgroup_index": subgroup_idx,
							},
							"meta": {
								"chunking_variant": "adaptive_section",
								"mode": "prose_adaptive_split",
							},
						}
					)
					chunk_counter += 1

			sent_start += step

	chunks = _merge_short_text_chunks(chunks, min_chunk_chars=min_chunk_chars, max_chunk_chars=max_chunk_chars)
	chunks = _reindex_chunk_ids(chunks, doc_id)
	return chunks
