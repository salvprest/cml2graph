from dataclasses import dataclass
from typing import Any

from .utils.helpers import extract_contents, ref_id
from .utils.types import CLASS_STEREOTYPES, RELATION_STEREOTYPES


@dataclass
class Issue:
    severity: str # "error" | "warning"
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.message}"


def validate_model(data: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []

    if not isinstance(data, dict):
        issues.append(Issue("error", "Root JSON value is not an object."))
        return issues

    contents = extract_contents(data)
    if contents is None:
        issues.append(
            Issue("error", "Cannot find model contents (no 'contents' key).")
        )
        return issues

    classes: list[dict] = []
    relations: list[dict] = []
    generalizations: list[dict] = []

    for item in contents:
        tp = item.get("type")
        if tp == "Class":
            classes.append(item)
        elif tp == "Relation":
            relations.append(item)
        elif tp == "Generalization":
            generalizations.append(item)

    seen_ids: set[str] = set()
    for cls in classes:
        cid = cls.get("id")
        if not cid:
            issues.append(Issue("error", f"Class without 'id': {cls}"))
            continue
        if cid in seen_ids:
            issues.append(Issue("warning", f"Duplicate class id: {cid}"))
        seen_ids.add(cid)

        stereotype = cls.get("stereotype")
        if stereotype and stereotype not in CLASS_STEREOTYPES:
            issues.append(Issue("warning", f"Unknown class stereotype '{stereotype}' on {cid}"))
        if not cls.get("name"):
            issues.append(Issue("warning", f"Class {cid} has no name."))

    for rel in relations:
        rid = rel.get("id")
        if not rid:
            issues.append(Issue("error", f"Relation without 'id': {rel}"))
            continue

        stereotype = rel.get("stereotype")
        if stereotype and stereotype not in RELATION_STEREOTYPES:
            issues.append(Issue("warning", f"Unknown relation stereotype '{stereotype}' on {rid}"))

        props = rel.get("properties") or []
        for prop in props:
            pt = prop.get("propertyType", {})
            r = pt.get("id") if isinstance(pt, dict) else None
            if r and r not in seen_ids:
                issues.append(Issue("warning", f"Relation {rid} references unknown class {r}"))

    for gen in generalizations:
        gid = gen.get("id")
        if not gid:
            issues.append(Issue("error", f"Generalization without 'id': {gen}"))
            continue
        general_ref = ref_id(gen.get("general"))
        specific_ref = ref_id(gen.get("specific"))
        if general_ref and general_ref not in seen_ids:
            issues.append(Issue("warning",f"Generalization {gid}: general {general_ref} not found"))
        if specific_ref and specific_ref not in seen_ids:
            issues.append(Issue("warning", f"Generalization {gid}: specific {specific_ref} not found"))

    return issues