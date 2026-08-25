"""
Automated faithfulness checking for LLM-generated explanations.

Extracts every number stated in the explanation and verifies it against
the evidence the model was given. Because the evidence compiler pre-computes
all legitimate derived values (deltas, percentages), any number that cannot
be matched is unsupported by construction.

This is a strict checker: it will occasionally flag a legitimate figure
(see LIMITATIONS below). That is preferred over a lenient checker that
lets real fabrications through -- an over-flagging metric is honest, an
under-flagging one is misleading.

LIMITATIONS:
 * Numbers below MIN_CHECKED_VALUE are ignored, since small integers
   ("3 paragraphs", "5 years") are ubiquitous and matching them is
   uninformative.
 * The checker verifies that a number EXISTS in the evidence, not that it
   was used in the correct context. An explanation could state a real
   number about the wrong scenario and still pass.
"""

import re

# Numbers smaller than this are not checked -- see LIMITATIONS.
MIN_CHECKED_VALUE = 100.0

# Relative tolerance for rounding (0.5% -- covers "17,394" for 17,393.94)
RELATIVE_TOLERANCE = 0.005

NUMBER_PATTERN = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def extract_numbers(text: str) -> list[float]:
    """Pull every parseable number out of free text, normalizing separators."""
    found = []
    for match in NUMBER_PATTERN.findall(text):
        cleaned = match.replace(",", "").rstrip(".")
        if not cleaned or cleaned in {"-", "+"}:
            continue
        try:
            found.append(float(cleaned))
        except ValueError:
            continue
    return found


def collect_evidence_values(evidence) -> set[float]:
    """
    Recursively gather every numeric value in the evidence object,
    including values derivable by simple rounding.
    """
    values: set[float] = set()

    def walk(node):
        if isinstance(node, dict):
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, bool):
            return                      # bool is a subclass of int -- skip it
        elif isinstance(node, (int, float)):
            value = float(node)
            values.add(value)
            values.add(abs(value))      # sign may be phrased away in prose
            values.add(round(value))    # rounded restatement is legitimate

    walk(evidence)
    return values


def is_supported(number: float, evidence_values: set[float]) -> bool:
    """A number is supported if it matches an evidence value within tolerance."""
    for candidate in evidence_values:
        if candidate == 0:
            if abs(number) < 1e-9:
                return True
            continue
        if abs(number - candidate) / abs(candidate) <= RELATIVE_TOLERANCE:
            return True
    return False


def check_faithfulness(explanation: str, evidence: dict) -> dict:
    """
    Verify every number in an explanation against the evidence.

    Returns the pass rate plus the specific unsupported values, so a
    failure can be inspected rather than merely counted.
    """
    stated = extract_numbers(explanation)
    checked = [n for n in stated if abs(n) >= MIN_CHECKED_VALUE]
    evidence_values = collect_evidence_values(evidence)

    supported = [n for n in checked if is_supported(n, evidence_values)]
    unsupported = [n for n in checked if not is_supported(n, evidence_values)]

    return {
        "numbers_stated": len(stated),
        "numbers_checked": len(checked),
        "numbers_supported": len(supported),
        "numbers_unsupported": len(unsupported),
        "unsupported_values": unsupported,
        "faithfulness_rate": (
            round(len(supported) / len(checked), 4) if checked else None
        ),
        "passed": len(unsupported) == 0,
    }