"""Create only the user-authorized operational insertion; old versions untouched."""
import json
import shutil
from pathlib import Path
from project2_v03_calibration import digest, save

ROOT=Path(__file__).resolve().parents[1]
AUTH='''【用户授权（本人决定，日期 2026-10-05，原文如下）】
授权你创建 specs/project2/v0.3.1 操作性修订，仅限以下四项；其余一律不得改动，包括 S08.1 删失规则、预算公式、熔断阈值（32 次依赖、12 次 LLM）、S07、场景集合、门禁、held-out 规则、CL-01 至 CL-08 的其他决定。
超出范围的改动一律停止并报告。把本授权原文与日期写入 specs/project2/v0.3.1/approval_addendum.md，v0.1、v0.2、v0.3 文件保持不变。

1. 防睡眠与检测：
   - 在标定运行器进程内调用 Windows SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED) 阻止睡眠。
     不得修改系统电源设置，不得安装任何软件。
   - 后台线程每 5 秒记录一次墙钟心跳；相邻心跳间隔超过 30 秒，该批次标记为 host_suspended。
   - 条件允许时（psutil 已安装）检查是否接电，不接电就停止并报告。
2. 重跑：用与批次 1 完全相同的任务集、抽样规则、种子和 300 个槽位，运行批次 2。
   批次 1 的所有记录原样保留，标注"批次 1：因主机睡眠删失，未用于决策"，不得删除或改写。
3. 决策规则：预算只用第一个完整、无删失的批次得出，不同批次不得混合、平均或逐条剔除。
   批次 2 若被判 host_suspended 或删失，保留记录并自动运行批次 3；批次 3 仍失败就停止并报告。
   若删失不是由睡眠引起（心跳无间隔），按 S08.1 原样处理并停止，不得重跑。
4.（可选，可删）预算上限只升不降：
   最终硬上限 = max(已签署值, 按 v0.3 公式算出的值)，其中依赖 16、LLM 6 为已签署值。
   墙钟超时仍按 v0.3 公式由实测得出。该条在批次 2 开跑前登记并写入哈希。'''


def build():
    old=ROOT/'specs/project2/v0.3';new=ROOT/'specs/project2/v0.3.1'
    if (new/'version_manifest.json').exists(): raise ValueError('v0.3.1 already frozen')
    new.mkdir(parents=True,exist_ok=True)
    protocol_path=ROOT/'evals/project2-v1/calibration_v031/protocol.json'
    protocol=json.loads(protocol_path.read_text(encoding='utf-8'))
    for name,sha in protocol['protected_files'].items():
        if digest(ROOT/name)!=sha: raise ValueError('Protected file changed: '+name)
    for f in old.iterdir():
        if f.is_file() and f.name not in {'check_docs.py','delta.md','delta.json','approval_addendum.md','version_manifest.json'}:
            shutil.copyfile(f,new/f.name)
    addition='''### S08.2 v0.3.1 操作性标定批次（2026-10-05 实现前授权）

1. 防睡眠仅在标定运行器调用线程内使用 Windows SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)，结束/异常时恢复ES_CONTINUOUS；不改电源设置、不安装软件。后台线程每5秒追加墙钟心跳；任意相邻间隔严格大于30秒，整个批次标记host_suspended。若已安装psutil，启动前和运行中检查接电；明确未接电停止。未安装/无电池传感器如实登记，不安装依赖、不伪造接电证据。
2. 批次2完全复用批次1的50任务、抽样规则、种子20261005、两路径各3重复的300槽位；全部失败/拒答/耗时保留。批次1目录逐文件哈希锁定、原样保留；在新账本标注“批次 1：因主机睡眠删失，未用于决策”，不改写其任何文件。
3. 决策只用第一个完整300槽位、无删失且无host_suspended的批次；不混合、平均或逐条剔除。批次2因心跳睡眠间隔无效，保留并自动运行独立批次3；批次3仍无效停止。无心跳睡眠间隔的删失按S08.1停止，不重跑；其他运行器错误/断电也停止。依赖P95>32或LLM P95>12仍触发原熔断，不提高上限。S08.1删失规则、原公式、S07、场景集合、门禁及held-out规则保持原文。
4. 采用可选“调用上限只升不降”，在批次2开跑前登记：依赖硬上限=max(16,ceil(1.25*ceil(P95)))；LLM硬上限=max(6,ceil(1.25*ceil(P95)))。墙钟无90秒下限，仍为两路径较大实测P95的1.5倍。协议、批次原记录/心跳、结果/决策及各SHA256冻结，生产默认只读取通过校验的所选完整批次。

操作协议：`evals/project2-v1/calibration_v031/protocol.json`，SHA256：`PROTOCOL_SHA`；本规格副本`operation_protocol.json`逐字相同。新账本`batches.json`与`decision.json`只在运行后产生；没有证据不得写完成。其他CL决定和既有授权模型、范围及非目标均保持。

'''.replace('PROTOCOL_SHA',digest(protocol_path))
    original=(old/'spec.md').read_text(encoding='utf-8')
    anchor='<a id="s09"></a>'
    if original.count(anchor)!=1: raise ValueError('Insertion anchor changed')
    updated=original.replace(anchor,addition+anchor)
    (new/'spec.md').write_text(updated,encoding='utf-8')
    shutil.copyfile(protocol_path,new/'operation_protocol.json')
    changes=[{'file':'spec.md','category':'authorized_operational_insertion','old':anchor,'new':addition+anchor}]
    save(new/'delta.json',{'from_version':'v0.3','to_version':'v0.3.1','authorization_date':'2026-10-05',
         'changes':changes,'operational_items':4,'optional_floor_adopted':True,
         'protected_files':protocol['protected_files'],'batch1_files':protocol['batch1_files'],
         'protocol_sha256':digest(protocol_path)})
    (new/'delta.md').write_text('# v0.3 → v0.3.1 操作性修订\n\n日期2026-10-05；授权发生在本次实现和批次2之前。仅在S08.1原文之后插入S08.2，其他设计正文/场景/矩阵/任务不改。\n\n- 进程内防睡眠、5秒墙钟心跳、>30秒整批无效及有条件接电检查。\n- 同一300槽位整批重跑；批次1原样保留，不用于预算决策。\n- 第一个完整无删失批次决定预算；只有睡眠无效批次2可自动批次3。\n- 采用预登记调用上限下限16/6，墙钟仍按原P95公式；原32/12熔断不变。\n\n精确旧/新插入及旧文件SHA256见delta.json；原故障和v0.3修订见未变的v0.3/delta.md。批次1全量证据见evals/project2-v1/calibration_v03/frozen_manifest.json。新批次未运行时不得宣称标定/门禁通过。\n',encoding='utf-8')
    (new/'approval_addendum.md').write_text('# v0.3.1 用户授权补充记录\n\n记录日期：2026-10-05。用户本人在本次实现/批次2运行之前于对话授权。未代填人工审阅栏。\n\n'+AUTH+'\n\n操作选择：第4项采用；协议哈希 `'+digest(protocol_path)+'`。\n\n版本 manifest SHA256：待生成\n',encoding='utf-8')


if __name__=='__main__': build()
