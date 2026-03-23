"""OntoUML metamodel constants and shared helpers."""

from .types import (
    CLASS_STEREOTYPES,
    RELATION_STEREOTYPES,
    NATURE_TYPES,
    STEREOTYPE_CATEGORY,
    RELATIONSHIP_TYPES,
    ASSOCIATION_NAME_SYNONYMS,
)
from .helpers import extract_contents, flatten_contents, ref_id

__all__ = [
    "CLASS_STEREOTYPES",
    "RELATION_STEREOTYPES",
    "NATURE_TYPES",
    "STEREOTYPE_CATEGORY",
    "RELATIONSHIP_TYPES",
    "ASSOCIATION_NAME_SYNONYMS",
    "extract_contents",
    "flatten_contents",
    "ref_id",
]