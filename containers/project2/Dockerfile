FROM python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src:/app/enterprise-ai-agent \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TECHQA_QUERY_DEVICE=cpu \
    PROJECT2_STATE_DIRECTORY=/app/.rag_data/project2_runtime \
    PROJECT2_RERANK_CACHE=/app/.rag_data/rerank_cache/cache.sqlite
WORKDIR /app
COPY .container-wheelhouse /wheels
COPY containers/project2/runtime.requirements.txt /runtime.requirements.txt
RUN python -m pip install --no-index --find-links=/wheels -r /runtime.requirements.txt \
    && python -m pip check && rm -rf /wheels
COPY src/rag /app/src/rag
COPY config /app/config
COPY enterprise-ai-agent/api /app/enterprise-ai-agent/api
COPY enterprise-ai-agent/agents /app/enterprise-ai-agent/agents
COPY enterprise-ai-agent/tools /app/enterprise-ai-agent/tools
COPY enterprise-ai-agent/models /app/enterprise-ai-agent/models
COPY enterprise-ai-agent/vectorstore /app/enterprise-ai-agent/vectorstore
COPY specs/project2 /app/specs/project2
COPY evals/protocol_v0/baseline_v0.config.json /app/evals/protocol_v0/baseline_v0.config.json
COPY evals/project2-v1/calibration_v031 /app/evals/project2-v1/calibration_v031
COPY evals/project2-v1/calibration_v03 /app/evals/project2-v1/calibration_v03
RUN mkdir -p /app/.rag_data/models /app/.rag_data/techqa_semantic /app/.rag_data/project2_runtime /app/.rag_data/rerank_cache /app/audit/project2-v1 \
    && chown -R 10001:10001 /app/.rag_data /app/audit
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --start-period=180s --interval=10s --timeout=3s \
    CMD python -c "import urllib.request,json; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=2))['ready']"
CMD ["python", "-m", "uvicorn", "api.project2_container_main:app", "--host", "0.0.0.0", "--port", "8000"]
