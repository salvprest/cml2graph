import logging
from dataclasses import dataclass
from typing import Any, Literal

from .utils.types import ELEMENT_LAYER, RELATIONSHIP_TYPES

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Issue:
    severity: Literal["error", "warning"]
    message: str
    context_id: str | None = None

    def __str__(self) -> str:
        tag = f"[{self.context_id}] " if self.context_id else ""
        return f"{self.severity.upper()}: {tag}{self.message}"


def validate_model(data: dict[str, Any]) -> list[Issue]:
    """
    Return a list of Issues found in *data*.

    Rules
    -----
    * ``elements`` and ``relationships`` keys must exist.
    * Every element must carry ``id`` and ``type``.
    * Every relationship must carry ``id``, ``type``, ``sourceId``, ``targetId``.
    * ``sourceId`` / ``targetId`` must reference an existing element.
    * Unknown types produce warnings, not errors.
    """
    issues: list[Issue] = []

    # topblevel keys
    if "elements" not in data:
        issues.append(Issue("error", "Missing 'elements' key in model."))
    if "relationships" not in data:
        issues.append(Issue("error", "Missing 'relationships' key in model."))
    if any(i.severity == "error" for i in issues):
        return issues

    # elements
    element_ids: set[str] = set()
    for idx, elem in enumerate(data["elements"]):
        eid = elem.get("id")
        etype = elem.get("type")

        if not eid:
            issues.append(Issue("error", f"Element at index {idx} missing 'id'."))
            continue
        if eid in element_ids:
            issues.append(Issue("warning", "Duplicate element id.", context_id=eid))
        element_ids.add(eid)

        if not etype:
            issues.append(Issue("error", "Element missing 'type'.", context_id=eid))
        elif etype not in ELEMENT_LAYER:
            issues.append(
                Issue("warning", f"Unknown element type '{etype}'.", context_id=eid)
            )

        if not elem.get("name"):
            issues.append(Issue("warning", "Element has empty name.", context_id=eid))

    # relationships
    for idx, rel in enumerate(data["relationships"]):
        rid = rel.get("id")
        rtype = rel.get("type")
        src = rel.get("sourceId")
        tgt = rel.get("targetId")

        if not rid:
            issues.append(
                Issue("error", f"Relationship at index {idx} missing 'id'.")
            )
            continue

        if not rtype:
            issues.append(Issue("error", "Relationship missing 'type'.", context_id=rid))
        elif rtype not in RELATIONSHIP_TYPES:
            issues.append(
                Issue("warning", f"Unknown relationship type '{rtype}'.", context_id=rid)
            )

        for field, value in (("sourceId", src), ("targetId", tgt)):
            if not value:
                issues.append(
                    Issue("error", f"Relationship missing '{field}'.", context_id=rid)
                )
            elif value not in element_ids:
                issues.append(
                    Issue(
                        "error",
                        f"'{field}' references non‑existent element '{value}'.",
                        context_id=rid,
                    )
                )

    return issues