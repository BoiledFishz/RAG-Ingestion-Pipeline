"""Load the project's optional .env without overriding explicitly exported variables."""

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
