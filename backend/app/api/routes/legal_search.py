# What: 引入 FastAPI 路由、依赖和异常工具。
# Why: 这里要定义法规检索接口。
# How: APIRouter 定义路由，Depends 注入数据库，HTTPException 返回错误。
from fastapi import APIRouter, Depends, HTTPException

# What: 引入数据库会话类型。
# Why: 检索接口需要从数据库构建或获取法规索引。
# How: 使用 SQLAlchemy Session 类型标注。
from sqlalchemy.orm import Session

# What: 引入数据库依赖。
# Why: FastAPI 需要通过 Depends(get_db) 获取数据库连接。
# How: 复用 db/session.py 里的 get_db。
from app.db.session import get_db

# What: 引入检索请求和响应模型。
# Why: API 输入输出要有明确结构。
# How: 使用 legal_search.py 里定义的 Pydantic schema。
from app.schemas.legal_search import (
    LegalHybridSearchHitResponse,
    LegalHybridSearchRequest,
    LegalHybridSearchResponse,
    LegalVectorSearchHitResponse,
    LegalVectorSearchRequest,
    LegalVectorSearchResponse,
)

from app.services.legal_index_manager import (
    get_or_build_legal_bm25_index,
    get_or_build_legal_vector_index,
    rebuild_legal_vector_index_from_db,
)



# What: 引入向量检索函数。
# Why: 获取索引后，需要执行 query top-k 检索。
# How: 使用 search_legal_vector_index。
from app.services.legal_vector_index import search_legal_vector_index
from app.services.legal_hybrid_retriever import search_legal_hybrid

# What: 定义法规检索路由对象。
# Why: 所有法规检索相关接口都挂在 /legal-search 下。
# How: prefix 指定路径前缀，tags 用于 Swagger 分组。
router = APIRouter(prefix="/legal-search", tags=["legal-search"])


# What: 定义法规向量检索接口。
# Why: 前端或后续智能体需要通过 API 检索相关法规片段。
# How: POST /api/v1/legal-search/vector。
@router.post("/vector", response_model=LegalVectorSearchResponse)
async def search_legal_vectors(
    # What: 接收检索请求体。
    # Why: 请求体里包含 query、top_k、过滤条件等。
    # How: FastAPI 自动解析 JSON 到 LegalVectorSearchRequest。
    payload: LegalVectorSearchRequest,

    # What: 注入数据库连接。
    # Why: 第一次检索时可能需要从数据库构建索引。
    # How: 使用 Depends(get_db)。
    db: Session = Depends(get_db),
) -> LegalVectorSearchResponse:
    # What: 捕获运行时错误。
    # Why: embedding 配置缺失、向量维度异常等要返回明确错误。
    # How: RuntimeError 转成 HTTP 500。
    try:
        # What: 判断是否强制重建索引。
        # Why: 法规库更新后，需要刷新内存索引。
        # How: payload.rebuild_index 为 True 时走重建逻辑。
        if payload.rebuild_index:
            index = await rebuild_legal_vector_index_from_db(db)
        else:
            index = await get_or_build_legal_vector_index(db)

        # What: 执行向量检索。
        # Why: 从法规索引里找出和 query 最相关的 chunks。
        # How: 使用 search_legal_vector_index，传入过滤条件和 top_k。
        hits = await search_legal_vector_index(
            index=index,
            query=payload.query,
            top_k=payload.top_k,
            countries=payload.countries,
            domains=payload.domains,
            min_score=payload.min_score,
        )

    # What: 处理运行时异常。
    # Why: API 不能把内部异常直接暴露成杂乱 traceback。
    # How: 转成 FastAPI 的 HTTPException。
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # What: 返回结构化检索响应。
    # Why: 调用方需要 query、索引状态和命中法规列表。
    # How: 把 LegalVectorHit 转成 LegalVectorSearchHitResponse。
    return LegalVectorSearchResponse(
        query=payload.query,
        index_chunk_count=index.chunk_count,
        index_dimension=index.dimension,
        hits=[
            LegalVectorSearchHitResponse(
                score=hit.score,
                record_id=hit.chunk.record_id,
                country=hit.chunk.country,
                domain=hit.chunk.domain,
                law_title=hit.chunk.law_title,
                chunk_index=hit.chunk.chunk_index,
                text=hit.chunk.text,
            )
            for hit in hits
        ],
    )



# What: 定义法规 Hybrid 检索接口。
# Why: Hybrid 同时使用向量语义召回和 BM25 关键词召回，效果比单一检索更稳。
# How: POST /api/v1/legal-search/hybrid。
@router.post("/hybrid", response_model=LegalHybridSearchResponse)
async def search_legal_hybrid_endpoint(
    payload: LegalHybridSearchRequest,
    db: Session = Depends(get_db),
) -> LegalHybridSearchResponse:
    try:
        if payload.rebuild_index:
            vector_index = await rebuild_legal_vector_index_from_db(db)
        else:
            vector_index = await get_or_build_legal_vector_index(db)

        bm25_index = get_or_build_legal_bm25_index(db)

        hits = await search_legal_hybrid(
            vector_index=vector_index,
            bm25_index=bm25_index,
            query=payload.query,
            top_k=payload.top_k,
            vector_candidate_k=payload.vector_candidate_k,
            bm25_candidate_k=payload.bm25_candidate_k,
            vector_weight=payload.vector_weight,
            bm25_weight=payload.bm25_weight,
            countries=payload.countries,
            domains=payload.domains,
        )

    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return LegalHybridSearchResponse(
        query=payload.query,
        vector_index_chunk_count=vector_index.chunk_count,
        bm25_index_chunk_count=bm25_index.chunk_count,
        index_dimension=vector_index.dimension,
        hits=[
            LegalHybridSearchHitResponse(
                hybrid_score=hit.hybrid_score,
                vector_score=hit.vector_score,
                bm25_score=hit.bm25_score,
                record_id=hit.chunk.record_id,
                country=hit.chunk.country,
                domain=hit.chunk.domain,
                law_title=hit.chunk.law_title,
                chunk_index=hit.chunk.chunk_index,
                text=hit.chunk.text,
            )
            for hit in hits
        ],
    )