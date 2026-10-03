"""Command-line answer or complete diagnostic trace, emitted through logging."""

from __future__ import annotations

import argparse
import asyncio
import logging

from agents.rag_agent.factory import build_agent, open_store
from models.schemas import QueryRequest
from models.settings import Settings


async def main(query: str, trace: bool = False) -> None:
    settings = Settings.from_env()
    store = open_store(settings)
    try:
        result = await build_agent(settings, store).run(QueryRequest(query=query))
        output = result if trace else result.response
        logging.getLogger(__name__).info("%s", output.model_dump_json(indent=2))
    finally:
        if store is not None:
            await store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    asyncio.run(main(args.query, args.trace))
