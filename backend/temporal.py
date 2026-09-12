from __future__ import annotations

from datetime import date
from .models import Document


def valid_at(doc: Document, when: date) -> bool:
    if doc.valid_from and when < doc.valid_from:
        return False
    if doc.valid_to and when > doc.valid_to:
        return False
    return True


def explain_validity(doc: Document, when: date) -> dict:
    result = {
        "document": doc.id,
        "date": when.isoformat(),
        "valid": valid_at(doc, when),
        "valid_from": doc.valid_from.isoformat() if doc.valid_from else None,
        "valid_to": doc.valid_to.isoformat() if doc.valid_to else None,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
    }
    if result["valid"]:
        result["reason"] = "document is valid at query time"
    elif doc.valid_from and when < doc.valid_from:
        result["reason"] = f"effective only from {doc.valid_from.isoformat()}"
    elif doc.valid_to and when > doc.valid_to:
        result["reason"] = f"expired after {doc.valid_to.isoformat()}"
    else:
        result["reason"] = "outside validity interval"
    return result
