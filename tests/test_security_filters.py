from __future__ import annotations

from rag.retrieval.filters import FilterPolicy


def test_security_filter_cannot_be_overridden() -> None:
    policy = FilterPolicy(
        system_filters={"status": "published", "tenant_id": "tenant-a"}
    )
    merged = policy.apply(
        {
            "status": "draft",
            "tenant_id": "tenant-b",
            "language": "en",
        }
    )
    assert merged["status"] == "published"
    assert merged["tenant_id"] == "tenant-a"
    assert merged["language"] == "en"
