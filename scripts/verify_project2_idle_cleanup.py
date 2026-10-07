"""One readiness/EOF cleanup probe, no QA input, retrieval or LLM request."""
from __future__ import annotations
import asyncio
import json
import logging
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'enterprise-ai-agent'));sys.path.insert(0,str(ROOT/'scripts'))
from agents.project2.rag_process import BoundedRAGProcess
from project2_v031_calibration import HostGuard
from project2_v03_report import read,save,sha

async def main():
    target=ROOT/'audit/project2-v1/v032_idle_cleanup'
    if target.exists():raise ValueError('Probe already registered; not a repeated gate')
    target.mkdir()
    log=ROOT/'audit/project2-v1/regression_repair1.log'
    text=log.read_text(encoding='utf-8-sig',errors='replace')
    save(target/'plan.json',{'source_log_sha256':sha(log),'new_QA_requests':0,'new_LLM_requests':0,
        'probe':'fresh local readiness, idle EOF shutdown; does not rerun completed 117 records',
        'previous_cleanup_failure_excerpt':text[-1800:]})
    runtime=BoundedRAGProcess(read(ROOT/'evals/protocol_v0/baseline_v0.config.json')['environment'])
    with HostGuard(target/'power'):
        try:
            ready=await runtime.start();process=runtime.process
            runtime.stop()
            passed=process.poll()==0 and runtime.process is None and runtime.cleanup_observation['mode']=='idle_eof'
            save(target/'result.json',{'passed':passed,'process_returncode':process.poll(),'pid':process.pid,
               'ready_worker_pid':ready['worker_pid'],'cleanup':runtime.cleanup_observation,
               'evidence_type':'真实运行','QA_requests':0,'LLM_requests':0,'old_records_rerun':False})
        finally:runtime.stop()
    if not passed:raise RuntimeError('Real idle EOF cleanup failed')

if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    asyncio.run(main())
