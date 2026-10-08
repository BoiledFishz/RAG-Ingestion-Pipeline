"""Container-only entry. Default Runtime and MultiAgent remain unchanged."""
import os
import logging
from pathlib import Path
logging.basicConfig(level=logging.INFO)
from api.project2_runtime_main import create_app
from agents.project2.container_transport import bridge_url
from agents.project2.container_cache import seed_cache


seed=os.getenv('PROJECT2_CACHE_SEED_SHA256')
if seed:
    logging.getLogger(__name__).info('P2_CACHE %s',seed_cache(Path('/cache-seed.sqlite'),Path('/app/.rag_data/rerank_cache/cache.sqlite'),seed))
app=create_app()
app.state.rag_runtime.environment['AGENT_OLLAMA_URL']=bridge_url(
    os.getenv('PROJECT2_OLLAMA_URL','http://host.docker.internal:11434'))
