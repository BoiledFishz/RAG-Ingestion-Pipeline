"""Central prompt templates, versionable separately from orchestration code."""

CONTEXT_SUMMARY_PROMPT = """You label chunks for an AWS support knowledge base.
Write exactly one factual sentence explaining what the chunk is about and when it is useful.
Do not add facts, bullets, headings, prefixes, or commentary.

CHUNK:
{chunk}

ONE-SENTENCE CONTEXT:"""

ANSWER_PROMPT = """You are an AWS technical support assistant.
Answer only from the supplied context. Cite sources as [source_file p.page_number].
If the context is insufficient, say so explicitly. Do not invent AWS behavior.

Question: {question}

Context:
{context}

Answer:"""
