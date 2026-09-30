"""Create the title text index explicitly; never build large indexes during queries."""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient, models

from models.settings import Settings

LOGGER = logging.getLogger(__name__)


def main() -> None:
    settings = Settings.from_env()
    if not settings.qdrant_url:
        raise ValueError("Set AGENT_QDRANT_URL for the full-corpus server index")
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=600)
    try:
        info = client.get_collection(settings.collection)
        if "title" not in info.payload_schema:
            client.create_payload_index(
                settings.collection, field_name="title", wait=True,
                field_schema=models.TextIndexParams(type=models.TextIndexType.TEXT,
                                                    tokenizer=models.TokenizerType.WORD,
                                                    min_token_len=1, lowercase=True),
            )
        LOGGER.info("Title text index is ready for %s", settings.collection)
    finally:
        client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
