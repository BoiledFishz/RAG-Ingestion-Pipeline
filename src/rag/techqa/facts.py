"""Query-derived requirements and explicit, non-truth-valued coverage diagnostics.

No dataset IDs, reference answers, or product-specific answers are used here.
Pattern matches identify candidate evidence, not factual sufficiency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RequiredFact:
    key: str
    description: str
    pattern: str


def required_facts(query: str) -> list[RequiredFact]:
    if re.search(r"\bCVE-\d{4}-\d+\b|\bvulnerabilit", query, re.IGNORECASE):
        return [
            RequiredFact("vulnerability", "Identify the requested vulnerability and its nature",
                         r"CVE-\d{4}-\d+|DESCRIPTION:|VULNERABILITY DETAILS"),
            RequiredFact("affected_versions", "State affected versions AND documented exposure "
                         "conditions; do not assume the user meets a condition",
                         r"AFFECTED PRODUCTS AND VERSIONS[\s\S]+\d+\.\d+|"
                         r"\d+\.\d+.*(?:install|collector)"),
            RequiredFact("remediation", "Report documented fix/remediation or where the "
                         "requested details are available; preserve version conditions",
                         r"fixpack|fix pack|APAR|upgraded|first fix|mitigations?\s+None"),
        ]
    options = list(dict.fromkeys(re.findall(
        r"\b[A-Za-z][A-Za-z0-9_]*-[A-Za-z0-9_-]*\d[A-Za-z0-9_-]*\b", query)))
    if (len(options) >= 2 and re.search(r"\bwhich\b|compar|difference|\bversions\b",
                                      query, re.IGNORECASE)):
        return [
            RequiredFact("option_a", "Explain the first named option: " + options[0],
                         re.escape(options[0])),
            RequiredFact("option_b", "Explain the second named option: " + options[1],
                         re.escape(options[1])),
            RequiredFact("selection_rule", "Give applicable product-version/OS/package "
                         "selection rules and a conditional recommendation; do not invent "
                         "differences absent from the evidence",
                         r"if you are running|version.*supports|single package|separate package|"
                         r"part number.*operating system"),
        ]
    if (re.search(r"(?:user.?name|password|credentials?)", query, re.IGNORECASE)
            and re.search(r"not (?:used|be(?:ing)? used)|instead.*(?:admin|user)|"
                          r"username is not", query, re.IGNORECASE)):
        return [RequiredFact("configured_identity", "Explain why configured credentials are "
                    "not being used and how to select the intended outbound identity, preserving "
                    "the premise that the supplied username/password are already correct",
                    r"component.managed authentication alias|componentAuthAlias|"
                    r"container.managed security|user\.name"),
                RequiredFact("required_steps", "Supply concrete applicable configuration steps "
                             "when changing credential selection; address why the configured "
                             "identity is replaced, not a different application's generic "
                             "connection error; do not merely repeat symptoms",
                             r"wsadmin|modify\w*|configure|set |AdminTask")]
    if (re.search(r"(?:activation|authorization) code", query, re.IGNORECASE)
            and re.search(r"new.*(?:computer|host|mac)|licens", query, re.IGNORECASE)):
        return [RequiredFact("activation_on_new_host", "Help activate/license the installed "
                    "product on the new host using the already-owned code; instructions only "
                    "for obtaining an existing code again do not answer that request",
                    r"authorization wizard|license.*(?:new|product)|authoriz|activat"),
                RequiredFact("required_steps", "Give complete applicable licensing steps, "
                             "keeping any error-message, OS and release prerequisites explicit",
                             r"\b[1-9][.)]\s|wizard|sudo|launch|enter|license the")]
    if re.search(r"\b(?:how|install|configure|resolve|fix|steps|procedure)\b", query,
                 re.IGNORECASE):
        return [RequiredFact("applicable_solution", "Answer the complete principal request "
                             "and its stated premises, rather than a merely related topic",
                             r"answer|solution|resolv|work.?around|because|configure|if|requires"),
                RequiredFact("required_steps", "Keep the chosen procedure complete with its "
                             "conditions and command arguments; one complete alternative is "
                             "enough unless the user requests all alternatives. A documented "
                             "single action such as installing named missing libraries is "
                             "complete without invented commands or extra verification steps",
                             r"\b[1-9][.)]\s|command|set |configure|install|solution|steps|"
                             r"--[A-Za-z][\w-]*")]
    return [RequiredFact("requested_answer", "Answer the principal factual request or give "
                         "an applicable cause/solution for the reported failure, retaining all "
                         "relevant premises and conditions", r"\S")]


def potential_coverage(query: str, text: str) -> tuple[str, ...]:
    """Candidate-selection hints; never used to declare an answer sufficient."""
    return tuple(f.key for f in required_facts(query)
                 if re.search(f.pattern, text, re.IGNORECASE))
