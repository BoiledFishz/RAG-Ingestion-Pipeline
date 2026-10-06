"""Service readiness is not an already-dispatched user query."""
import asyncio
import pytest
from agents.project2.rag_process import BoundedRAGProcess

def test_request_timeout_does_not_repeatedly_cancel_shared_service_initialization():
    async def exercise():
        released=asyncio.Event();starts=[]
        class Initialization(BoundedRAGProcess):
            async def _start(self):
                starts.append('service-init');await released.wait()
                return {'type':'ready','scope':'full'}
        runtime=Initialization({'AGENT_MODEL':'qwen2.5:7b'})
        with pytest.raises(TimeoutError):await asyncio.wait_for(runtime.start(),.01)
        assert len(starts)==1
        released.set()
        assert await runtime.start()=={'type':'ready','scope':'full'}
        assert len(starts)==1 and runtime.active_budget is None
    asyncio.run(exercise())
