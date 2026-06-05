# What: 引入 Pydantic 基础模型和字段工具。
# Why: FastAPI 的请求体和响应体都需要用 Pydantic 定义。
# How: BaseModel 定义结构，Field 定义默认值和校验规则。
from pydantic import BaseModel, Field


# What: 定义法规向量检索请求体。
# Why: 前端或调用方需要传 query、top_k、国家过滤、领域过滤等参数。
# How: 使用 Pydantic 模型接收 JSON 请求。
class LegalVectorSearchRequest(BaseModel):
    # What: 用户检索问题。
    # Why: 这是要转成 embedding 的核心查询文本。
    # How: FastAPI 从 JSON body 里读取 query。
    query: str

    # What: 返回结果数量。
    # Why: 后续大模型不应该接收太多法规片段。
    # How: 默认 8，限制在 1 到 20。
    top_k: int = Field(default=8, ge=1, le=20)

    # What: 国家或地区过滤。
    # Why: 可以只检索 China、Singapore、Vietnam 等范围。
    # How: 不传就是不过滤。
    countries: list[str] | None = None

    # What: 法规领域过滤。
    # Why: 可以只检索 cross_border_data、tax、employment 等领域。
    # How: 不传就是不过滤。
    domains: list[str] | None = None

    # What: 最低相似度分数。
    # Why: 可以过滤明显不相关的低分结果。
    # How: 不传就是不过滤。
    min_score: float | None = None

    # What: 是否强制重建索引。
    # Why: 法规库刚重新导入后，可能需要刷新内存索引。
    # How: 默认 False，只有需要刷新时传 True。
    rebuild_index: bool = False


# What: 定义单条法规检索命中响应。
# Why: API 返回时需要带分数、法规来源、chunk 文本。
# How: 从 LegalVectorHit 转换成这个响应模型。
class LegalVectorSearchHitResponse(BaseModel):
    # What: 相似度分数。
    # Why: 调用方需要知道命中结果排序依据。
    # How: 来自 LegalVectorHit.score。
    score: float

    # What: 法规记录 ID。
    # Why: 后续报告引用法规时要能追溯来源。
    # How: 来自 hit.chunk.record_id。
    record_id: str

    # What: 国家或地区。
    # Why: 展示和过滤时需要。
    # How: 来自 hit.chunk.country。
    country: str

    # What: 法规领域。
    # Why: 展示和过滤时需要。
    # How: 来自 hit.chunk.domain。
    domain: str

    # What: 法规标题。
    # Why: 检索结果不能只展示 ID。
    # How: 来自 hit.chunk.law_title。
    law_title: str

    # What: chunk 序号。
    # Why: 同一条法规会切成多段，需要知道命中了哪一段。
    # How: 来自 hit.chunk.chunk_index。
    chunk_index: int

    # What: 命中的法规正文片段。
    # Why: 后续风险分析和报告引用需要具体文本。
    # How: 来自 hit.chunk.text。
    text: str


# What: 定义法规向量检索响应。
# Why: API 需要返回检索结果和索引状态。
# How: 包含 query、索引规模、向量维度和 hits。
class LegalVectorSearchResponse(BaseModel):
    # What: 原始查询文本。
    # Why: 方便调用方确认本次检索的问题。
    # How: 原样返回 request.query。
    query: str

    # What: 索引里的 chunk 数量。
    # Why: 调试时可以确认是否查的是完整法规库。
    # How: 来自 index.chunk_count。
    index_chunk_count: int

    # What: 向量维度。
    # Why: 调试 embedding 模型是否正确。
    # How: 来自 index.dimension。
    index_dimension: int

    # What: 检索命中列表。
    # Why: 这是 API 的核心结果。
    # How: 按 score 从高到低返回。
    hits: list[LegalVectorSearchHitResponse]



# What: 定义 Hybrid 检索请求体。
# Why: Hybrid 检索需要 query、过滤条件、候选数量和融合权重。
# How: 继承 LegalVectorSearchRequest，复用 query/top_k/countries/domains/rebuild_index。
class LegalHybridSearchRequest(LegalVectorSearchRequest):
    # What: 向量候选数量。
    # Why: 融合前要多取一些语义候选，避免过早丢掉好结果。
    # How: 默认 30，限制在 1 到 100。
    vector_candidate_k: int = Field(default=30, ge=1, le=100)

    # What: BM25 候选数量。
    # Why: 融合前要多取一些关键词候选。
    # How: 默认 30，限制在 1 到 100。
    bm25_candidate_k: int = Field(default=30, ge=1, le=100)

    # What: 向量分数权重。
    # Why: 数据跨境问题需要语义理解，所以向量权重默认更高。
    # How: 默认 0.65，范围 0 到 1。
    vector_weight: float = Field(default=0.65, ge=0, le=1)

    # What: BM25 分数权重。
    # Why: 法规名、条款名、专有词需要关键词硬匹配。
    # How: 默认 0.35，范围 0 到 1。
    bm25_weight: float = Field(default=0.35, ge=0, le=1)


# What: 定义 Hybrid 单条命中响应。
# Why: 调试和展示时要同时看到融合分、向量分、BM25 分。
# How: 字段和 vector hit 类似，但多了三个分数。
class LegalHybridSearchHitResponse(BaseModel):
    # What: Hybrid 融合分。
    # Why: 最终排序依据。
    # How: vector_score 和 bm25_score 归一化加权得到。
    hybrid_score: float

    # What: 原始向量分。
    # Why: 用于判断语义召回贡献。
    # How: 来自 LegalHybridHit.vector_score。
    vector_score: float

    # What: 原始 BM25 分。
    # Why: 用于判断关键词召回贡献。
    # How: 来自 LegalHybridHit.bm25_score。
    bm25_score: float

    record_id: str
    country: str
    domain: str
    law_title: str
    chunk_index: int
    text: str


# What: 定义 Hybrid 检索响应。
# Why: API 要返回索引状态和融合命中结果。
# How: 包含 query、索引规模、向量维度和 hits。
class LegalHybridSearchResponse(BaseModel):
    query: str
    vector_index_chunk_count: int
    bm25_index_chunk_count: int
    index_dimension: int
    hits: list[LegalHybridSearchHitResponse]