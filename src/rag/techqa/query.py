"""Conservative query and operation checks, without inferring missing user facts."""

from __future__ import annotations

import re

SOCKET_COMPONENTS = {
    "gateway": r"\bSocket(?:\s+Java)?\s+Gateway\b|\bnco-g-socket(?:[-_]\w+)*\b",
    "probe": r"\bSocket(?:\s+Java)?\s+Probe\b|\bnco-p-socket(?:[-_]\w+)*\b",
}
REQUIREMENT_ERROR = re.compile(
    r"\b(?P<product>IBM(?:\s+[A-Za-z]+){1,10})\s+version\b"
    r"[\s\S]{0,160}?\brequires\s+version\s+(?P<required>\d+(?:\.\d+)+)",
    re.IGNORECASE,
)


def requirement_error_conflict(query: str, applicability: str) -> bool:
    """Reject an older minimum-version *error premise* for the same named product.

    This compares two explicit requirement errors, never unrelated component
    versions, an absent fix-pack number, or a generic guide's installation floor.
    """
    premise = re.split(
        r"(?im)^\s*(?:CAUSE|RESOLVING THE PROBLEM|ANSWER|RESOLUTION)\s*:?\s*\n",
        applicability,
        maxsplit=1,
    )[0]

    def product(value: str) -> list[str]:
        return [word.removesuffix("s") for word in value.casefold().split() if word != "ibm"]

    for requested in REQUIREMENT_ERROR.finditer(query):
        for documented in REQUIREMENT_ERROR.finditer(premise):
            if product(requested["product"]) != product(documented["product"]):
                continue
            requested_version = tuple(int(v) for v in requested["required"].split("."))
            documented_version = tuple(int(v) for v in documented["required"].split("."))
            if documented_version < requested_version:
                return True
    return False


def component_conflict(query: str, title: str) -> bool:
    """Distinguish explicitly named Socket Gateway/Probe components, not versions."""
    requested = {name for name, pattern in SOCKET_COMPONENTS.items()
                 if re.search(pattern, query, re.IGNORECASE)}
    documented = {name for name, pattern in SOCKET_COMPONENTS.items()
                  if re.search(pattern, title, re.IGNORECASE)}
    return bool(requested and documented and requested.isdisjoint(documented))


def searchable_identifier(query: str) -> bool:
    """Recognize versioned package/file names as well as APIs and error codes."""
    return bool(re.search(
        r"\b[A-Za-z0-9_.-]+:[A-Za-z0-9_*.-]+\b|"
        r"\b[A-Za-z][a-z]+(?:[A-Z][A-Za-z0-9]+)+\b|"
        r"\b[A-Z]{2,}[A-Z0-9_]*\d[A-Z0-9_]*\b|"
        r"\b[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)+\b|"
        r"\b\d+(?:\.\d+){1,4}\b",
        query,
    ))


def protected_terms(query: str) -> set[str]:
    values = re.findall(
        r"\b(?:[A-Za-z]+[A-Z][A-Za-z0-9]*|[\w.-]+:[\w*.-]+|[A-Za-z0-9_:/.-]*\d"
        r"[A-Za-z0-9_:/.-]*|not|never|without|cannot)\b",
        query,
    )
    values += re.findall(r"不能|不要|未开启|没有|禁止", query)
    return {value.casefold() for value in values}


def operation_conflict(query: str, title: str, applicability: str) -> bool:
    """Reject rollback-only fault premises for installation/upgrade requests.

    Only the source's problem/question premise is inspected. A rollback mentioned
    in solution steps does not establish that the document is a rollback fault.
    """
    rollback = r"\b(?:roll(?:ing|ed)?\s*back|rollback|downgrad\w*)\b"
    if re.search(rollback, query, re.IGNORECASE) or not re.search(
        r"\b(?:install(?:ing|ation)?|upgrad\w*)\b", query, re.IGNORECASE,
    ):
        return False
    premise = re.split(
        r"(?im)^\s*(?:CAUSE|RESOLVING THE PROBLEM|ANSWER|RESOLUTION)\s*:?\s*\n",
        applicability,
        maxsplit=1,
    )[0]
    return bool(re.search(rollback, title + "\n" + premise, re.IGNORECASE))
