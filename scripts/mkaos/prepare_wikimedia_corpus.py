#!/usr/bin/env python3
"""Prepare a pinned Wikimedia XML dump into attributable, deduplicated JSONL splits.

This is a reproducible preparation pipeline, not a legal approval or a claim that
Wikipedia is suitable as the sole source for a general-purpose language model.
The source archive is intentionally not committed to the repository.
"""
from __future__ import annotations

import argparse
import bz2
import hashlib
import html
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SOURCE_ID = "wikimedia-trwiki-pages-articles-20261001"
RELEASE = "20261001"
BASE_URL = f"https://dumps.wikimedia.org/trwiki/{RELEASE}"
ARCHIVE_NAME = f"trwiki-{RELEASE}-pages-articles-multistream.xml.bz2"
ARCHIVE_URL = f"{BASE_URL}/{ARCHIVE_NAME}"
LICENSE_URL = "https://meta.wikimedia.org/wiki/Terms_of_use/Creative_Commons_4.0/en"
DUMP_DOCS_URL = "https://meta.wikimedia.org/wiki/Data_dumps"
MIN_TEXT_CHARS = 300
MAX_TEXT_CHARS = 200_000

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
# Conservative phone-like patterns: redact only long digit sequences with separators.
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s()./-]{8,}\d)(?!\w)")
URL_RE = re.compile(r"https?://\S+", re.I)
SPACE_RE = re.compile(r"[ \t\f\v]+")
MANY_NEWLINES_RE = re.compile(r"\n{3,}")
WIKILINK_RE = re.compile(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]")
EXTERNAL_LINK_RE = re.compile(r"\[(?:https?://\S+)\s*([^\]]*)\]", re.I)
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
REF_RE = re.compile(r"<ref\b[^>]*>.*?</ref\s*>|<ref\b[^>]*/\s*>", re.I | re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
CATEGORY_RE = re.compile(r"\[\[Kategori:[^\]]*\]\]", re.I)
TABLE_RE = re.compile(r"\{\|.*?\|\}", re.S)
REDIRECT_RE = re.compile(r"^\s*#(?:redirect|yönlendirme)\b", re.I)
DISAMBIGUATION_TITLE_RE = re.compile(r"\(anlam ayrımı\)\s*$", re.I)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    # MD5 is used only to verify Wikimedia's published transport checksum;
    # SHA-256 is also recorded as the stronger local content identifier.
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_md5(checksum_file: Path, archive_name: str) -> str:
    for line in checksum_file.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^\s*([0-9a-fA-F]{32})\s+\*?(.+?)\s*$", line)
        if match and Path(match.group(2)).name == archive_name:
            return match.group(1).lower()
    raise ValueError(f"Archive {archive_name!r} not found in upstream MD5 list {checksum_file}")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, wanted: str) -> str:
    for child in element:
        if local_name(child.tag) == wanted:
            return child.text or ""
    return ""


def page_fields(page: ET.Element) -> dict[str, str] | None:
    title = child_text(page, "title").strip()
    namespace = child_text(page, "ns").strip()
    page_id = child_text(page, "id").strip()
    if namespace != "0" or not page_id or not title:
        return None
    revision = next((node for node in page if local_name(node.tag) == "revision"), None)
    if revision is None:
        return None
    revision_id = child_text(revision, "id").strip()
    timestamp = child_text(revision, "timestamp").strip()
    text = ""
    for node in revision.iter():
        if local_name(node.tag) == "text":
            text = node.text or ""
            break
    return {
        "title": title,
        "page_id": page_id,
        "revision_id": revision_id,
        "timestamp": timestamp,
        "wikitext": text,
    }


def strip_wikitext(wikitext: str) -> str:
    """Strip markup using mwparserfromhell, then normalize residual markup."""
    try:
        import mwparserfromhell
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency mwparserfromhell. Install requirements-corpus.txt."
        ) from exc

    code = mwparserfromhell.parse(wikitext)
    text = code.strip_code(normalize=True, collapse=True, keep_template_params=False)
    text = COMMENT_RE.sub(" ", text)
    text = REF_RE.sub(" ", text)
    text = CATEGORY_RE.sub(" ", text)
    text = TABLE_RE.sub(" ", text)
    text = WIKILINK_RE.sub(r"\1", text)
    text = EXTERNAL_LINK_RE.sub(r"\1", text)
    text = HTML_TAG_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    lines = [SPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = MANY_NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def redact_contact_details(text: str) -> tuple[str, int]:
    """Mask common direct-contact strings; this is not a complete PII detector."""
    text, emails = EMAIL_RE.subn("[E-POSTA ÇIKARILDI]", text)
    text, phones = PHONE_RE.subn("[TELEFON NUMARASI ÇIKARILDI]", text)
    return text, emails + phones


def content_digest(text: str) -> str:
    canonical = unicodedata.normalize("NFC", text)
    canonical = SPACE_RE.sub(" ", canonical).strip().casefold()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def document_split(page_id: str, seed: str = f"mkaos-{RELEASE}-document-split-v1") -> str:
    """Stable page-level 90/5/5 split. Documents are never split into chunks."""
    value = int(hashlib.sha256(f"{seed}:{page_id}".encode("utf-8")).hexdigest()[:8], 16) % 100
    if value < 90:
        return "train"
    if value < 95:
        return "validation"
    return "test"


def iter_pages(archive: Path) -> Iterator[ET.Element]:
    # Remove processed page elements from the root as well as clearing them;
    # otherwise a multi-million-page dump leaves millions of empty nodes in RAM.
    with bz2.open(archive, "rb") as stream:
        context = ET.iterparse(stream, events=("start", "end"))
        _, root = next(context)
        stack = [root]
        for event, element in context:
            if event == "start":
                stack.append(element)
                continue
            if local_name(element.tag) == "page":
                yield element
                element.clear()
                if len(stack) >= 2:
                    stack[-2].remove(element)
            if stack and stack[-1] is element:
                stack.pop()


def prepare(archive: Path, output_dir: Path, checksum_file: Path | None) -> dict[str, Any]:
    if not archive.is_file():
        raise FileNotFoundError(archive)
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_sha256 = sha256_file(archive)
    archive_md5 = md5_file(archive)
    expected = expected_md5(checksum_file, archive.name) if checksum_file else None
    if expected and archive_md5 != expected:
        raise ValueError(
            f"Upstream MD5 mismatch: local={archive_md5}, published={expected}. "
            "Refusing to process a potentially corrupted download."
        )

    # A single content digest prevents identical text appearing in multiple splits.
    seen_content: set[str] = set()
    counts: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    output_hashes = {name: hashlib.sha256() for name in ("train", "validation", "test")}
    output_bytes = Counter()
    output_paths = {name: output_dir / f"{name}.jsonl" for name in output_hashes}
    total_pages = 0
    retained_chars = 0
    redaction_events = 0

    with (output_paths["train"].open("wb") as train,
          output_paths["validation"].open("wb") as validation,
          output_paths["test"].open("wb") as test):
        streams = {"train": train, "validation": validation, "test": test}
        for page in iter_pages(archive):
            total_pages += 1
            fields = page_fields(page)
            if fields is None:
                counts["excluded_non_main_namespace_or_missing_revision"] += 1
                continue
            if DISAMBIGUATION_TITLE_RE.search(fields["title"]):
                counts["excluded_disambiguation_title"] += 1
                continue
            if REDIRECT_RE.search(fields["wikitext"]):
                counts["excluded_redirect"] += 1
                continue
            text = strip_wikitext(fields["wikitext"])
            text, redactions = redact_contact_details(text)
            redaction_events += redactions
            if len(text) < MIN_TEXT_CHARS:
                counts["excluded_too_short"] += 1
                continue
            if len(text) > MAX_TEXT_CHARS:
                counts["excluded_too_long"] += 1
                continue
            digest = content_digest(text)
            if digest in seen_content:
                counts["excluded_exact_duplicate_text"] += 1
                continue
            seen_content.add(digest)

            split = document_split(fields["page_id"])
            record = {
                "record_id": f"{SOURCE_ID}:{fields['page_id']}",
                "source_id": SOURCE_ID,
                "source_release": RELEASE,
                "page_id": fields["page_id"],
                "revision_id": fields["revision_id"],
                "revision_timestamp": fields["timestamp"],
                "title": fields["title"],
                "url": f"https://tr.wikipedia.org/wiki/{fields['title'].replace(' ', '_')}",
                "text_sha256": digest,
                "split": split,
                "text": text,
                "attribution": (
                    "Text from Turkish Wikipedia; contributors are credited through the "
                    "article history URL. See the source license and reuse terms."
                ),
                "license": "CC BY-SA 4.0 and/or GFDL; per-page/imported-content exceptions require review",
                "license_url": LICENSE_URL,
            }
            line = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
            streams[split].write(line)
            output_hashes[split].update(line)
            output_bytes[split] += len(line)
            split_counts[split] += 1
            retained_chars += len(text)
            counts["retained_documents"] += 1
            if redactions:
                counts["documents_with_contact_redactions"] += 1

    output_files = {
        split: {
            "path": path.name,
            "sha256": output_hashes[split].hexdigest(),
            "bytes": output_bytes[split],
            "documents": split_counts[split],
        }
        for split, path in output_paths.items()
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": "mkaos-trwiki-20261001-cleaned-v1",
        "status": "prepared_pending_human_rights_privacy_and_content_review",
        "source": {
            "source_id": SOURCE_ID,
            "project": "Turkish Wikipedia (Wikimedia dump service)",
            "release": RELEASE,
            "archive_name": archive.name,
            "archive_url": ARCHIVE_URL,
            "archive_bytes": archive.stat().st_size,
            "archive_sha256": archive_sha256,
            "archive_md5_local": archive_md5,
            "upstream_md5": expected,
            "dump_documentation_url": DUMP_DOCS_URL,
            "license_terms_url": LICENSE_URL,
            "license_summary": (
                "Wikimedia text is commonly available under CC BY-SA and GFDL; check the "
                "applicable version, attribution/share-alike duties, and article-level exceptions."
            ),
        },
        "preparation": {
            "script": "scripts/mkaos/prepare_wikimedia_corpus.py",
            "python": sys.version.split()[0],
            "mwparserfromhell": __import__("mwparserfromhell").__version__,
            "text_normalization": "Unicode NFC; whitespace collapsed; markup stripped",
            "deduplication": "SHA-256 of NFC + whitespace-collapsed + casefolded cleaned text; exact duplicates only",
            "split_strategy": "stable SHA-256 bucket from page ID; document-level 90/5/5; seed mkaos-20261001-document-split-v1",
            "minimum_text_characters": MIN_TEXT_CHARS,
            "maximum_text_characters": MAX_TEXT_CHARS,
            "privacy_filter": (
                "common email and phone-like strings masked; this is not comprehensive PII, "
                "sensitive-content, copyright-exception, or legal review"
            ),
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
        "counts": {
            "xml_pages_seen": total_pages,
            "documents_by_split": dict(split_counts),
            "retained_total": sum(split_counts.values()),
            "retained_text_characters": retained_chars,
            "contact_redaction_events": redaction_events,
            "filters": dict(counts),
        },
        "outputs": output_files,
        "approval": {
            "training_rights_review": "pending_human_review",
            "privacy_and_sensitive_content_review": "pending_human_review",
            "attribution_and_share_alike_implementation_review": "pending_human_review",
            "weight_redistribution_review": "not_approved",
            "production_model_training_allowed": False,
            "checkpoint_publication_allowed": False,
            "notes": (
                "This manifest records provenance and preparation, not legal clearance. "
                "Do not mark this source approved or publish trained weights based on this run alone."
            ),
        },
    }
    manifest_path = output_dir / "corpus-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Pinned Wikimedia .xml.bz2 archive")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--upstream-md5-file", type=Path, help="Official Wikimedia MD5 list for the same release")
    args = parser.parse_args()
    manifest = prepare(args.archive, args.output_dir, args.upstream_md5_file)
    print(json.dumps({
        "dataset_id": manifest["dataset_id"],
        "archive_sha256": manifest["source"]["archive_sha256"],
        "outputs": manifest["outputs"],
        "counts": manifest["counts"],
        "approval": manifest["approval"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
