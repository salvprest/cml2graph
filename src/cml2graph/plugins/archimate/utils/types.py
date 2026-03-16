"""ArchiMate domain constants and the canonical layer mapping."""


RELATIONSHIP_TYPES: frozenset[str] = frozenset({
    "Access",
    "Aggregation",
    "Assignment",
    "Association",
    "Composition",
    "Flow",
    "Influence",
    "Realization",
    "Serving",
    "Specialization",
    "Triggering",
})


ELEMENT_LAYER: dict[str, str] = {
    # ---------- STRATEGY ----------
    "Resource":      "Strategy",
    "Capability":    "Strategy",
    "CourseOfAction":"Strategy",
    "ValueStream":   "Strategy",

    # ---------- BUSINESS ----------
    "BusinessActor":        "Business",
    "BusinessRole":         "Business",
    "BusinessCollaboration":"Business",
    "BusinessInterface":    "Business",
    "BusinessProcess":      "Business",
    "BusinessFunction":     "Business",
    "BusinessInteraction":  "Business",
    "BusinessEvent":        "Business",
    "BusinessService":      "Business",
    "BusinessObject":       "Business",
    "Contract":             "Business",
    "Representation":       "Business",
    "Product":              "Business",

    # ---------- APPLICATION ----------
    "ApplicationComponent":     "Application",
    "ApplicationCollaboration": "Application",
    "ApplicationInterface":     "Application",
    "ApplicationFunction":      "Application",
    "ApplicationInteraction":  "Application",
    "ApplicationProcess":       "Application",
    "ApplicationEvent":         "Application",
    "ApplicationService":       "Application",
    "DataObject":               "Application",

    # ---------- TECHNOLOGY ----------
    "Node":                "Technology",
    "Device":              "Technology",
    "SystemSoftware":      "Technology",
    "TechnologyCollaboration":"Technology",
    "TechnologyInterface": "Technology",
    "Path":                "Technology",
    "CommunicationNetwork":"Technology",
    "TechnologyFunction":   "Technology",
    "TechnologyProcess":    "Technology",
    "TechnologyInteraction":"Technology",
    "TechnologyEvent":      "Technology",
    "TechnologyService":    "Technology",
    "Artifact":             "Technology",

    # ---------- PHYSICAL ----------
    "Equipment":           "Physical",
    "Facility":            "Physical",
    "DistributionNetwork": "Physical",
    "Material":            "Physical",

    # ---------- MOTIVATION ----------
    "Stakeholder":  "Motivation",
    "Driver":       "Motivation",
    "Assessment":   "Motivation",
    "Goal":         "Motivation",
    "Outcome":      "Motivation",
    "Principle":    "Motivation",
    "Requirement":  "Motivation",
    "Constraint":   "Motivation",
    "Meaning":      "Motivation",
    "Value":        "Motivation",

    # ---------- IMPLEMENTATION & MIGRATION ----------
    "WorkPackage":          "Implementation",
    "Deliverable":          "Implementation",
    "ImplementationEvent":  "Implementation",
    "Plateau":              "Implementation",
    "Gap":                  "Implementation",

    # ---------- COMPOSITE / OTHER ----------
    "Location": "Composite",
    "Grouping": "Composite",

    # ---------- JUNCTIONS ----------
    "Junction":    "Other",
    "AndJunction": "Other",
    "OrJunction":  "Other",
}