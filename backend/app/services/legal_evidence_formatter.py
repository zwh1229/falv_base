# What: 引入 Hybrid 检索命中结构。
# Why: 法规依据格式化器接收的是 LegalHybridHit 列表。
# How: 从 legal_hybrid_retriever.py 导入 LegalHybridHit。
from app.services.legal_hybrid_retriever import LegalHybridHit


# What: 默认最多格式化的法规依据数量。
# Why: 大模型上下文不能无限塞法规片段。
# How: 默认取前 8 条 Hybrid 命中结果。
DEFAULT_EVIDENCE_TOP_K = 8


# What: 默认每条法规片段最大字符数。
# Why: 单个 chunk 太长会挤占 prompt 空间。
# How: 默认每条最多保留 1500 字。
DEFAULT_EVIDENCE_TEXT_MAX_CHARS = 1500


# What: 截断长文本。
# Why: 法规 chunk 过长时，大模型上下文会变得臃肿。
# How: 超过 max_chars 就截断，并加省略提示。
def truncate_text(text: str, max_chars: int = DEFAULT_EVIDENCE_TEXT_MAX_CHARS) -> str:
    # What: 处理无效长度。
    # Why: max_chars 小于等于 0 时不应该返回正文。
    # How: 直接返回空字符串。
    if max_chars <= 0:
        return ""

    # What: 清理正文前后空格。
    # Why: 格式化后的法规依据要干净。
    # How: strip 去掉首尾空白。
    cleaned_text = text.strip()

    # What: 判断是否需要截断。
    # Why: 没超过长度就保留完整文本。
    # How: 长度小于等于 max_chars 时直接返回。
    if len(cleaned_text) <= max_chars:
        return cleaned_text

    # What: 返回截断后的文本。
    # Why: 保留主要内容，同时告诉模型后面被省略。
    # How: 截取前 max_chars 个字符并追加提示。
    return cleaned_text[:max_chars].strip() + "\n...[法规片段已截断]"


# What: 格式化分数。
# Why: 证据里保留分数方便调试，但不需要太多小数。
# How: 保留 4 位小数。
def format_score(score: float) -> str:
    # What: 返回固定小数位字符串。
    # Why: prompt 和日志里看起来更整齐。
    # How: 使用 f-string 的 .4f。
    return f"{score:.4f}"


# What: 格式化单条法规依据。
# Why: 大模型需要看到法规来源、命中分数和具体正文。
# How: 把 LegalHybridHit 转成结构化文本块。
def format_one_legal_evidence(
    hit: LegalHybridHit,
    evidence_no: int,
    max_text_chars: int = DEFAULT_EVIDENCE_TEXT_MAX_CHARS,
) -> str:
    # What: 截断法规正文。
    # Why: 防止单条依据过长。
    # How: 调用 truncate_text。
    evidence_text = truncate_text(hit.chunk.text, max_text_chars)

    # What: 生成法规依据文本。
    # Why: 后续 risk_analyzer 会把这段内容放进大模型 prompt。
    # How: 使用清晰字段组织来源、分数和正文。
    return "\n".join(
        [
            f"[法规依据 {evidence_no}]",
            f"法规ID：{hit.chunk.record_id}",
            f"国家/地区：{hit.chunk.country}",
            f"法规领域：{hit.chunk.domain}",
            f"法规标题：{hit.chunk.law_title}",
            f"Chunk序号：{hit.chunk.chunk_index}",
            f"Hybrid分数：{format_score(hit.hybrid_score)}",
            f"Vector分数：{format_score(hit.vector_score)}",
            f"BM25分数：{format_score(hit.bm25_score)}",
            "法规正文片段：",
            evidence_text,
        ]
    )


# What: 格式化多条法规依据。
# Why: 风险分析 prompt 需要一整个法规依据区块。
# How: 遍历 Hybrid hits，逐条格式化后用空行分隔。
def format_legal_evidence_block(
    hits: list[LegalHybridHit],
    max_items: int = DEFAULT_EVIDENCE_TOP_K,
    max_text_chars: int = DEFAULT_EVIDENCE_TEXT_MAX_CHARS,
) -> str:
    # What: 处理空命中结果。
    # Why: 没有法规依据时也要给大模型明确提示。
    # How: 返回固定提示文本。
    if not hits:
        return "未检索到可用法规依据。"

    # What: 限制法规依据数量。
    # Why: 避免 prompt 太长。
    # How: 只取前 max_items 条。
    selected_hits = hits[:max_items]

    # What: 格式化每条法规依据。
    # Why: 每条依据都需要编号，方便大模型引用。
    # How: enumerate 从 1 开始编号。
    evidence_items = [
        format_one_legal_evidence(
            hit=hit,
            evidence_no=index,
            max_text_chars=max_text_chars,
        )
        for index, hit in enumerate(selected_hits, start=1)
    ]

    # What: 返回完整法规依据区块。
    # Why: 后续可以直接拼进风险分析 prompt。
    # How: 标题 + 多条法规依据，用空行分隔。
    return "【法规依据】\n\n" + "\n\n".join(evidence_items)