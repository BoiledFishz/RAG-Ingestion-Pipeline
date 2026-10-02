"""Offline tests use the committed official TechQA excerpts, never a generated KB."""

import os

os.environ["TECHQA_PROFILE"] = "fixture"
os.environ["TECHQA_RERANKER"] = "lexical"
os.environ["MODEL_PROVIDER"] = "demo"
