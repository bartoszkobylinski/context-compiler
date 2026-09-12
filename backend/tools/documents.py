from __future__ import annotations

from datetime import date
from pathlib import Path
import frontmatter

from ..models import Document


def _parse_date(value):
    if value in (None, "", "null"):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_corpus(corpus_dir: str | Path) -> dict[str, Document]:
    corpus: dict[str, Document] = {}
    for path in sorted(Path(corpus_dir).glob("*.md")):
        post = frontmatter.load(path)
        meta = post.metadata
        doc = Document(
            id=meta["id"],
            title=meta["title"],
            body=post.content.strip(),
            published_at=_parse_date(meta.get("published_at")),
            valid_from=_parse_date(meta.get("valid_from")),
            valid_to=_parse_date(meta.get("valid_to")),
            supersedes=meta.get("supersedes"),
            authority=meta.get("authority", "unknown"),
            domains=list(meta.get("domains", [])),
            references=list(meta.get("references", [])),
            path=str(path),
        )
        corpus[doc.id] = doc
    return corpus


def open_document(corpus: dict[str, Document], document_id: str) -> dict:
    doc = corpus[document_id]
    return {
        "id": doc.id,
        "title": doc.title,
        "body": doc.body,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "valid_from": doc.valid_from.isoformat() if doc.valid_from else None,
        "valid_to": doc.valid_to.isoformat() if doc.valid_to else None,
        "authority": doc.authority,
        "references": doc.references,
        "supersedes": doc.supersedes,
    }


def get_versions(corpus: dict[str, Document], title: str) -> list[dict]:
    docs = [d for d in corpus.values() if d.title.lower() == title.lower()]
    docs.sort(key=lambda d: (d.valid_from or date.min, d.published_at or date.min))
    return [open_document(corpus, d.id) for d in docs]


def follow_reference(corpus: dict[str, Document], document_id: str, reference_id: str) -> dict:
    source = corpus[document_id]
    if reference_id not in source.references:
        raise ValueError(f"{reference_id!r} is not referenced by {document_id!r}")
    return open_document(corpus, reference_id)
