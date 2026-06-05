# What: 引入 dataclass。
# Why: Hybrid 命中结果需要一个清晰的数据结构。
# How: 使用 @dataclass 自动生成初始化方法。
from dataclasses import dataclass

# What: 引入 BM25 索引和搜索函数。
# Why: Hybrid 检索需要关键词召回结果。
# How: 从 legal_bm25_index.py 导入。
from app.services.legal_bm25_index import LegalBM25Index, search_legal_bm25_index

# What: 引入法规 chunk 结构。
# Why: Hybrid 最终返回的每条结果都对应一个 LegalChunk。
# How: 复用 legal_chunker.py 里的 LegalChunk。
from app.services.legal_chunker import LegalChunk

# What: 引入向量索引和搜索函数。
# Why: Hybrid 检索需要语义召回结果。
# How: 从 legal_vector_index.py 导入。
from app.services.legal_vector_index import LegalVectorIndex, search_legal_vector_index


# What: 默认 Hybrid 返回数量。
# Why: 最终给大模型的法规片段不能太多。
# How: 默认返回 top 8。
DEFAULT_HYBRID_TOP_K = 8

# What: 默认向量候选数量。
# Why: 融合前要多召回一些候选，避免过早截断。
# How: 默认从向量检索取 30 条候选。
DEFAULT_VECTOR_CANDIDATE_K = 30

# What: 默认 BM25 候选数量。
# Why: 关键词召回也要多拿一些候选参与融合。
# How: 默认从 BM25 取 30 条候选。
DEFAULT_BM25_CANDIDATE_K = 30

# What: 默认向量权重。
# Why: 数据跨境合规问题通常需要语义理解，向量分数权重略高。
# How: Hybrid 分数里向量归一化分数占 0.65。
DEFAULT_VECTOR_WEIGHT = 0.65

# What: 默认 BM25 权重。
# Why: 法规名、条款术语、专有名词需要关键词精确匹配兜底。
# How: Hybrid 分数里 BM25 归一化分数占 0.35。
DEFAULT_BM25_WEIGHT = 0.35


# What: 定义 Hybrid 检索命中结果。
# Why: 最终结果要同时展示融合分、向量分和 BM25 分。
# How: chunk 保存法规片段，三个 score 保存不同来源的分数。
@dataclass
class LegalHybridHit:
    # What: 命中的法规 chunk。
    # Why: 后续风险分析要引用这段法规正文。
    # How: 使用 LegalChunk 保存来源和文本。
    chunk: LegalChunk

    # What: Hybrid 融合分数。
    # Why: 最终排序使用这个分数。
    # How: 向量归一化分数和 BM25 归一化分数加权得到。
    hybrid_score: float

    # What: 原始向量相似度分数。
    # Why: 方便调试语义召回效果。
    # How: 来自 search_legal_vector_index。
    vector_score: float

    # What: 原始 BM25 分数。
    # Why: 方便调试关键词召回效果。
    # How: 来自 search_legal_bm25_index。
    bm25_score: float


# What: 生成 chunk 唯一键。
# Why: 同一个 chunk 可能同时被向量和 BM25 命中，需要去重融合。
# How: 用 record_id 和 chunk_index 组合。
def build_chunk_key(chunk: LegalChunk) -> str:
    return f"{chunk.record_id}:{chunk.chunk_index}"


# What: 归一化分数字典。
# Why: 向量分数和 BM25 分数量级不同，不能直接相加。
# How: 使用 min-max 归一化到 0 到 1。
def normalize_score_map(score_map: dict[str, float]) -> dict[str, float]:
    if not score_map:
        return {}

    min_score = min(score_map.values())
    max_score = max(score_map.values())

    if max_score == min_score:
        return {
            key: 1.0 if score > 0 else 0.0
            for key, score in score_map.items()
        }

    return {
        key: (score - min_score) / (max_score - min_score)
        for key, score in score_map.items()
    }


# What: 做 Hybrid 法规检索。
# Why: 单纯向量容易漏法规名硬匹配，单纯 BM25 又不懂语义，融合后更稳。
# How: 向量召回 + BM25 召回 + 分数归一化 + 加权排序。
async def search_legal_hybrid(
    vector_index: LegalVectorIndex,
    bm25_index: LegalBM25Index,
    query: str,
    top_k: int = DEFAULT_HYBRID_TOP_K,
    vector_candidate_k: int = DEFAULT_VECTOR_CANDIDATE_K,
    bm25_candidate_k: int = DEFAULT_BM25_CANDIDATE_K,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
    bm25_weight: float = DEFAULT_BM25_WEIGHT,
    countries: list[str] | None = None,
    domains: list[str] | None = None,
) -> list[LegalHybridHit]:
    if top_k <= 0:
        return []

    if not query.strip():
        return []

    vector_hits = await search_legal_vector_index(
        index=vector_index,
        query=query,
        top_k=vector_candidate_k,
        countries=countries,
        domains=domains,
    )

    bm25_hits = search_legal_bm25_index(
        index=bm25_index,
        query=query,
        top_k=bm25_candidate_k,
        countries=countries,
        domains=domains,
        min_score=0.0,
    )

    chunks_by_key: dict[str, LegalChunk] = {}
    vector_scores: dict[str, float] = {}
    bm25_scores: dict[str, float] = {}

    for hit in vector_hits:
        key = build_chunk_key(hit.chunk)
        chunks_by_key[key] = hit.chunk
        vector_scores[key] = hit.score

    for hit in bm25_hits:
        key = build_chunk_key(hit.chunk)
        chunks_by_key[key] = hit.chunk
        bm25_scores[key] = hit.score

    normalized_vector_scores = normalize_score_map(vector_scores)
    normalized_bm25_scores = normalize_score_map(bm25_scores)

    hybrid_hits: list[LegalHybridHit] = []

    for key, chunk in chunks_by_key.items():
        normalized_vector_score = normalized_vector_scores.get(key, 0.0)
        normalized_bm25_score = normalized_bm25_scores.get(key, 0.0)

        hybrid_score = (
            vector_weight * normalized_vector_score
            + bm25_weight * normalized_bm25_score
        )

        hybrid_hits.append(
            LegalHybridHit(
                chunk=chunk,
                hybrid_score=hybrid_score,
                vector_score=vector_scores.get(key, 0.0),
                bm25_score=bm25_scores.get(key, 0.0),
            )
        )

    hybrid_hits.sort(key=lambda hit: hit.hybrid_score, reverse=True)

    return hybrid_hits[:top_k]