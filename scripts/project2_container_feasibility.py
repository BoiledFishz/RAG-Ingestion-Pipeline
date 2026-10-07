"""Read local disk/runtime inventory. No Docker pull/build, cloud or installations."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from project2_v031_calibration import save
ROOT=Path(__file__).resolve().parents[1]
def main():
    from summarize_project2 import stage_verdict
    from project2_v03_report import read
    if stage_verdict(read(ROOT/'audit/project2-v1/v033_chap13_gate.json'))!='passed':raise ValueError('Chap13 gate required')
    receipt=read(ROOT/'evals/project2-v1/ch13_v033/heldout_receipt.json')
    if not receipt or receipt['status']!='completed':raise ValueError('Confirmatory run must finish before Chap14')
    assets=[ROOT/'.rag_data/techqa_full.sqlite',ROOT/'.rag_data/techqa_semantic',ROOT/'.rag_data/models/minilm',ROOT/'.rag_data/project2_runtime']
    sizes={p.relative_to(ROOT).as_posix():sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) if p.is_dir() else p.stat().st_size if p.exists() else 0 for p in assets}
    disk=shutil.disk_usage(ROOT);which=shutil.which('docker');fallback=Path('C:/Program Files/Docker/Docker/resources/bin/docker.exe')
    docker=which or (str(fallback) if fallback.is_file() else None)
    commands=[];ready=False;images=[]
    if docker:
        for args in [('version','--format','{{json .}}'),('info','--format','{{json .}}'),('image','ls','--format','{{json .}}')]:
            r=subprocess.run([docker,*args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
            commands.append({'arguments':list(args),'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if args[0]=='version':ready=r.returncode==0
            if args[0]=='image' and r.returncode==0:images=[json.loads(x) for x in r.stdout.splitlines()]
    reason='本机没有可用Docker CLI；Chap14真实容器门禁未执行，Chap15未进入' if not docker else 'Docker daemon不可用；不得安装/启动外部服务或用配置代替真实门禁' if not ready else None
    # Full index remains external and read-only; never duplicate it in layers.
    report={'status':'blocked' if reason else 'feasible_pending_build','reason':reason,'evidence_type':'真实运行（本地资源盘点）','docker_cli':docker,'docker_ready':ready,'commands':commands,'local_images':images,'asset_bytes':sizes,'disk_free_bytes':disk.free,'full_chunks':json.loads((ROOT/'.rag_data/techqa_semantic/manifest.json').read_text(encoding='utf-8'))['chunks'],'mount_plan':{'corpus_and_vectors':'read-only host mounts; exclude from build context and image layers','embedding_model':'pinned local read-only mount; local_files_only','ollama':'existing local host service; no download or paid remote model','state':'dedicated retained named volume; stop never deletes volume'},'cloud_evaluated':False,'software_installed':False}
    target=ROOT/'audit/project2-v1/container_feasibility.json'
    if target.exists():raise ValueError('Feasibility evidence already registered')
    save(target,report)
    md='# Chap14 容器可行性\n\n实际本机盘点；尚未构建或运行容器。\n\n'
    md+='\n'.join('- '+k+f'：{v/1024**3:.3f} GiB' for k,v in sizes.items())
    md+=f"\n\n全量索引{report['full_chunks']} Chunk；工作区盘剩余{disk.free/1024**3:.3f} GiB。Docker CLI={docker}，daemon可用={ready}。\n\n"
    md+='全文/FAISS/元数据与嵌入模型使用本机只读挂载，不复制到镜像；避免309万Chunk的大体积构建上下文和双份磁盘。状态卷独立保留，停止不删除。生成模型沿用本机Ollama，不能拉模型、拉远端镜像或安装系统依赖。冷启动需同时容纳FAISS、SQLite页缓存、MiniLM、生成模型和容器内存；盘点不能代替真实就绪/状态恢复门禁。\n\n'
    md+='停止原因：'+(reason or '资源盘点通过；还需离线干净构建与真实容器门禁。')+'\n'
    (ROOT/'specs/project2/container_feasibility.md').write_text(md,encoding='utf-8')
    print(json.dumps({'status':report['status'],'reason':reason,'asset_bytes':sizes},ensure_ascii=False))
    return 1 if reason else 0
if __name__=='__main__':raise SystemExit(main())
