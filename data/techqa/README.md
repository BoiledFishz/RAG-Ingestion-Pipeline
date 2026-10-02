# 官方 IBM TechQA 可复现样本

来源：https://github.com/ibm/techqa 指向的 PrimeQA/TechQA 归档。
许可：CDLA-Permissive-v1.0.pdf。文档版权归原提供者；本目录仅作注明来源的格式转换和选样。

`documents.json` 保留官方 41 篇文档的 ID、标题、text 和 metadata；`questions.json` 是原始 training 的
前 12 条可回答题和前 3 条不可回答题。额外文档来自各题 DOC_IDS 的前两项，作为真实干扰项。
这些是功能测试和训练样本，不是全量库，也不是独立测试集。

`mixed/` 的 12 个 Markdown 保存原标题与正文，另外两个 PDF 将 Streams 原文分别渲染为可提取文字和图片。
没有改写产品行为，也没有编造问答。`.techqa-manifest.json` 记录格式转换和原文 SHA-256。
扫描/OCR 的分辨率和字体可能造成识别差异，这种差异不表示上游文档不同。

重建：先获取官方 core 原始文件，再从根目录运行 `python scripts/prepare_techqa.py`。
`manifest.json` 是来源、选样规则及逐文档原文哈希清单。
