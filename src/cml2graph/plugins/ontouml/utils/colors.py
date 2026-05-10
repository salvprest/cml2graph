"""
OntoUML Smart Paint color scheme.
Maps nature (restrictedTo) + stereotype to standard colors.

Based on the OntoUML Visual Paradigm plugin color standards.
See: SmartColoringUtils.java
"""

from __future__ import annotations

# Color constants (RGB → hex)
COLOR_ABSTRACT = "#FFFFFF"                 # RGB(255, 255, 255)
COLOR_COLLECTIVE = "#FFDADD"               # RGB(255, 218, 221)
COLOR_COLLECTIVE_DARK = "#FF99A3"          # RGB(255, 153, 163)
COLOR_EVENT = "#FCFCD4"                    # RGB(252, 252, 212)
COLOR_SITUATION = "#FCE0C0"                # RGB(252, 224, 192)
COLOR_MODE = "#C0EDFF"                     # RGB(192, 237, 255)
COLOR_MODE_DARK = "#70D7FF"                # RGB(112, 215, 255)
COLOR_FUNCTIONAL_COMPLEX = "#FFDADD"       # RGB(255, 218, 221)
COLOR_FUNCTIONAL_COMPLEX_DARK = "#FF99A3"  # RGB(255, 153, 163)
COLOR_QUALITY = "#C0EDFF"                  # RGB(192, 237, 255)
COLOR_QUALITY_DARK = "#70D7FF"             # RGB(112, 215, 255)
COLOR_QUANTITY = "#FFDADD"                 # RGB(255, 218, 221)
COLOR_QUANTITY_DARK = "#FF99A3"            # RGB(255, 153, 163)
COLOR_RELATOR = "#D3FFD3"                  # RGB(211, 255, 211)
COLOR_RELATOR_DARK = "#99FF99"             # RGB(153, 255, 153)
COLOR_TYPE = "#D3D3FC"                     # RGB(211, 211, 252)
COLOR_NON_SPECIFIC = "#E0E0E0"             # RGB(224, 224, 224)

# Ultimate sortal stereotypes (get darker shade)
_ULTIMATE_SORTALS: frozenset[str] = frozenset({
    "kind", "collective", "quantity", "relator", "quality", "mode",
})


def get_color_for_class(stereotype: str, nature: str) -> str:
    """Return hex color based on OntoUML Smart Paint standard.

    Color is determined by nature (restrictedTo); the stereotype controls
    whether the dark or light shade is used (ultimate sortals → dark).

    Args:
        stereotype: The class stereotype (kind, role, category, …).
        nature: Comma-separated restrictedTo values (e.g. "functional-complex").

    Returns:
        Hex color string such as ``"#FFDADD"``.
    """
    stereotype_lower = (stereotype or "").lower()
    nature = (nature or "").strip()

    if not nature:
        return COLOR_NON_SPECIFIC

    is_ultimate_sortal = stereotype_lower in _ULTIMATE_SORTALS

    # normalise separators, then split
    natures = [n.strip() for n in nature.replace(",", " ").split() if n.strip()]

    if len(natures) == 1:
        n = natures[0]

        if n == "abstract":
            return COLOR_ABSTRACT
        if n == "collective":
            return COLOR_COLLECTIVE_DARK if is_ultimate_sortal else COLOR_COLLECTIVE
        if n == "event":
            return COLOR_EVENT
        if n == "situation":
            return COLOR_SITUATION
        if n in ("intrinsic-mode", "extrinsic-mode"):
            return COLOR_MODE_DARK if is_ultimate_sortal else COLOR_MODE
        if n == "functional-complex":
            return COLOR_FUNCTIONAL_COMPLEX_DARK if is_ultimate_sortal else COLOR_FUNCTIONAL_COMPLEX
        if n == "quality":
            return COLOR_QUALITY_DARK if is_ultimate_sortal else COLOR_QUALITY
        if n == "quantity":
            return COLOR_QUANTITY_DARK if is_ultimate_sortal else COLOR_QUANTITY
        if n == "relator":
            return COLOR_RELATOR_DARK if is_ultimate_sortal else COLOR_RELATOR
        if n == "type":
            return COLOR_TYPE

    # Multiple natures
    natures_set = set(natures)

    # Both mode kinds together
    if natures_set == {"intrinsic-mode", "extrinsic-mode"}:
        return COLOR_MODE_DARK if is_ultimate_sortal else COLOR_MODE

    # Object natures: functional-complex, collective, quantity
    if natures_set.issubset({"functional-complex", "collective", "quantity"}):
        return COLOR_FUNCTIONAL_COMPLEX

    # Mode/Quality natures
    if natures_set.issubset({"intrinsic-mode", "extrinsic-mode", "quality"}):
        return COLOR_MODE

    return COLOR_NON_SPECIFIC
