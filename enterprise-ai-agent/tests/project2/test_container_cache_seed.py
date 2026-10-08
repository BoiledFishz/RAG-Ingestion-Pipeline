"""Cache migration verifies provenance before it writes anything."""
from pathlib import Path
import pytest


def test_cache_seed_rejects_wrong_hash_without_creating_a_file(tmp_path):
    from agents.project2.container_cache import seed_cache
    root=Path(__file__).resolve().parents[3]
    target=tmp_path/'cache.sqlite'
    with pytest.raises(ValueError,match='Cache seed hash mismatch'):
        seed_cache(root/'.rag_data/techqa_rerank_cache.sqlite',target,'0'*64)
    assert not target.exists()
