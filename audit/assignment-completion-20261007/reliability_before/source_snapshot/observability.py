"""Process-local transparent observation of the same stage as baseline v0."""
from typing import Any

def observe_pipeline(pipeline: Any, measurement: dict[str, Any]) -> None:
    original=pipeline.retrieve
    async def retrieve(*args: Any, **kwargs: Any) -> Any:
        outcome=await original(*args,**kwargs)
        measurement.update({'candidate_ids':[x.chunk_id for x in outcome.results],
                            'reranker_fallback':outcome.diagnostics.reranker_fallback,
                            'stage':'retrieval_pipeline_before_parent_expansion'})
        return outcome
    pipeline.retrieve=retrieve
