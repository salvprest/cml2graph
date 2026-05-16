"""
OntoUML metamodel constants.

Single source of truth for stereotype validation, category mapping,
nature types, and relationship types used throughout the plugin.
"""

from __future__ import annotations

# ── Class stereotypes grouped by meta-category ───────────────────

SORTAL_STEREOTYPES: frozenset[str] = frozenset({
    "kind", "subkind", "role", "phase",
    "collective", "quantity",
    "relator", "quality", "mode",
    "historicalRole", "historicalRoleMixin",
    "type", "enumeration", "datatype",
    "event", "situation",
})

NON_SORTAL_STEREOTYPES: frozenset[str] = frozenset({
    "category", "mixin", "phaseMixin", "roleMixin", "abstract",
})

CLASS_STEREOTYPES: frozenset[str] = SORTAL_STEREOTYPES | NON_SORTAL_STEREOTYPES

# ── Relation (association) stereotypes ───────────────────────────

RELATION_STEREOTYPES: frozenset[str] = frozenset({
    "material", "mediation", "characterization",
    "componentOf", "memberOf", "subCollectionOf", "subQuantityOf",
    "bringsAbout", "creation", "comparative",
    "externalDependence", "historicalDependence",
    "instantiation", "manifestation",
    "participation", "participational",
    "termination", "triggers",
    "derivation",
    "relation",
})

# Subset: part-whole relation stereotypes (mereology, drawn with diamond).
# participational is mereology and gets a diamond arrow.
PART_WHOLE_STEREOTYPES: frozenset[str] = frozenset({
    "componentOf", "memberOf", "subCollectionOf", "subQuantityOf",
    "participational",
})

# AggregationKind values (OntoUML Vocabulary canonical lowercase) ──
# Source: https://w3id.org/ontouml#AggregationKind
# composite -> filled diamond (*--), strong/inseparable parthood
# shared    -> hollow diamond (o--), weak/separable parthood
# none      -> plain association, no diamond
class AggregationKind:
    COMPOSITE = "composite"
    SHARED    = "shared"
    NONE      = "none"


# Maps each mereology stereotype to its canonical aggregation kind.
# memberOf is the only separable (shared/hollow) parthood; all others are
# inseparable (composite/filled). subCollectionOf is composite, not shared
# this differs from naive UML intuition.
MEREOLOGY_AGGREGATION_KIND: dict[str, str] = {
    "memberOf":        AggregationKind.SHARED,
    "componentOf":     AggregationKind.COMPOSITE,
    "subCollectionOf": AggregationKind.COMPOSITE,
    "subQuantityOf":   AggregationKind.COMPOSITE,
    "participational": AggregationKind.COMPOSITE,
}

# ── Nature / restrictedTo values ─────────────────────────────────

NATURE_TYPES: frozenset[str] = frozenset({
    "functional-complex", "collective", "quantity",
    "intrinsic-mode", "extrinsic-mode",
    "quality", "relator", "abstract",
    "event", "situation", "type",
})

# ── Default nature inferred from stereotype (fallback for skeletons) ─
# Used when restrictedTo is unavailable (e.g. mined patterns).
# TODO: Controll if we can infer nature reliably
DEFAULT_NATURE_BY_STEREOTYPE: dict[str, str] = {
    "kind": "functional-complex",
    "subkind": "functional-complex",
    "role": "functional-complex",
    "phase": "functional-complex",
    "collective": "collective",
    "quantity": "quantity",
    "historicalrole": "functional-complex",
    "relator": "relator",
    "quality": "quality",
    "mode": "intrinsic-mode",
    "event": "event",
    "situation": "situation",
    "type": "type",
    "enumeration": "type",
    "datatype": "type",
    # Non-sortals
    "category": "abstract",
    "mixin": "abstract",
    "phasemixin": "abstract",
    "rolemixin": "abstract",
    "abstract": "abstract",
    "historicalrolemixin": "abstract",
}

# ── Stereotype to semantic category ───────────────────────────────

STEREOTYPE_CATEGORY: dict[str, str] = {
    "kind": "Substantial", "subkind": "Substantial",
    "role": "Substantial", "phase": "Substantial",
    "collective": "Substantial", "quantity": "Substantial",
    "historicalRole": "Substantial",
    "relator": "Moment", "quality": "Moment", "mode": "Moment",
    "type": "Endurant", "enumeration": "Endurant", "datatype": "Endurant",
    "event": "Event", "situation": "Situation",
    "category": "NonSortal", "mixin": "NonSortal",
    "phaseMixin": "NonSortal", "roleMixin": "NonSortal",
    "abstract": "NonSortal", "historicalRoleMixin": "NonSortal",
}

# ── All edge types that can appear on the graph ──────────────────

RELATIONSHIP_TYPES: frozenset[str] = RELATION_STEREOTYPES | frozenset({
    "generalization",
})

# ── Synonym normalisation ────────────────────────────────────────
# Maps informal association names to canonical OntoUML stereotypes.

ASSOCIATION_NAME_SYNONYMS: dict[str, str] = {
    "involves":                       "mediation",
    "involves >":                     "mediation",
    "inheres in":                     "characterization",
    "inheres_in":                     "characterization",
    "< inheres in":                   "characterization",
    "inheres in >":                   "characterization",
    "inheresIn":                      "characterization",
    "inheresin":                      "characterization",
    "participates":                   "participation",
    "participation of":               "participation",
    "participated":                   "participation",
    "participatedin":                 "participation",
    "hasparticipant":                 "participation",
    "participa em":                   "participation",
    "participa":                      "participation",
    "participant_of":                 "participation",
    "participate":                    "participation",
    "participates in":                "participation",
    "participates of":                "participation",
    "participates to events of type": "participation",
    "participation":                  "participation",
    "participationof":                "participation",
    "externaly dependent in":         "externalDependence",
    "ext. dep. on":                   "externalDependence",
}