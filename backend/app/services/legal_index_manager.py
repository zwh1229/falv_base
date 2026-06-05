# What: 引入数据库会话类型。
# Why: 索引管理器需要从数据库读取 LegalRecord。
# How: 使用 SQLAlchemy 的 Session 类型标注。
from sqlalchemy.orm import Session

# What: 引入法规主记录模型。
# Why: 重建索引时要查询 legal_records 表。
# How: 从 app.models.legal 导入 LegalRecord。
from app.models.legal import LegalRecord

# What: 引入批量 chunk 构建函数。
# Why: 数据库里的法规记录需要先转成 chunks，才能 embedding。
# How: 使用 build_many_legal_chunks。
from app.services.legal_chunker import build_many_legal_chunks

# What: 引入向量索引能力。
# Why: 索引管理器负责构建和缓存 LegalVectorIndex。
# How: 使用 build_legal_vector_index 和 LegalVectorIndex。
from app.services.legal_vector_index import (
    DEFAULT_EMBEDDING_BATCH_SIZE,
    LegalVectorIndex,
    build_legal_vector_index,
)

from app.services.legal_bm25_index import (
    LegalBM25Index,
    build_legal_bm25_index,
)


# What: 定义内存缓存变量。
# Why: 向量索引构建成本较高，不应该每次检索都重建。
# How: 模块级变量保存当前进程里的 LegalVectorIndex。
_CACHED_LEGAL_VECTOR_INDEX: LegalVectorIndex | None = None
# What: 定义 BM25 索引缓存变量。
# Why: BM25 分词和建模也不应该每次检索都重复做。
# How: 模块级变量保存当前进程里的 LegalBM25Index。
_CACHED_LEGAL_BM25_INDEX: LegalBM25Index | None = None


# What: 获取当前缓存的 BM25 索引。
# Why: 后续 Hybrid 检索需要复用关键词索引。
# How: 直接返回模块级缓存变量。
def get_cached_legal_bm25_index() -> LegalBM25Index | None:
    return _CACHED_LEGAL_BM25_INDEX


# What: 获取或构建 BM25 索引。
# Why: 检索接口不应该每次都重新分词建 BM25。
# How: 缓存存在就返回，否则从数据库读取法规并构建。
def get_or_build_legal_bm25_index(db: Session) -> LegalBM25Index:
    global _CACHED_LEGAL_BM25_INDEX

    cached_index = get_cached_legal_bm25_index()

    if cached_index is not None and cached_index.chunk_count > 0:
        return cached_index

    records = db.query(LegalRecord).order_by(LegalRecord.record_id.asc()).all()

    chunks = build_many_legal_chunks(records)

    index = build_legal_bm25_index(chunks)

    _CACHED_LEGAL_BM25_INDEX = index

    return index


# What: 获取当前缓存的法规向量索引。
# Why: 检索接口可以先看内存里有没有现成索引。
# How: 直接返回模块级缓存变量。
def get_cached_legal_vector_index() -> LegalVectorIndex | None:
    return _CACHED_LEGAL_VECTOR_INDEX


# What: 清空法规检索索引缓存。
# Why: 法规数据重新导入后，向量索引和 BM25 索引都需要失效。
# How: 把两个模块级缓存变量都设置为 None。
def clear_legal_vector_index_cache() -> None:
    global _CACHED_LEGAL_VECTOR_INDEX
    global _CACHED_LEGAL_BM25_INDEX

    _CACHED_LEGAL_VECTOR_INDEX = None
    _CACHED_LEGAL_BM25_INDEX = None


# What: 从数据库重建法规向量索引。
# Why: 第一次检索前，或者法规数据更新后，需要重新 embedding 全部法规 chunks。
# How: 查询 LegalRecord -> 构建 chunks -> 构建 LegalVectorIndex -> 写入缓存。
async def rebuild_legal_vector_index_from_db(
    db: Session,
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> LegalVectorIndex:
    global _CACHED_LEGAL_VECTOR_INDEX

    # What: 查询全部法规记录。
    # Why: 向量索引要覆盖当前数据库里的法规库。
    # How: 按 record_id 排序，保证每次构建顺序稳定。
    records = db.query(LegalRecord).order_by(LegalRecord.record_id.asc()).all()

    # What: 把法规记录转换成 chunks。
    # Why: embedding 的单位是 chunk，不是整条 LegalRecord。
    # How: 使用 build_many_legal_chunks 批量读取正文、清洗、切块。
    chunks = build_many_legal_chunks(records)

    # What: 构建向量索引。
    # Why: 后续检索要基于向量相似度。
    # How: 分批调用 embedding，并生成 LegalVectorIndex。
    index = await build_legal_vector_index(
        chunks,
        batch_size=batch_size,
    )

    # What: 写入内存缓存。
    # Why: 后续检索可以直接复用索引，不用重复 embedding。
    # How: 赋值给模块级变量。
    _CACHED_LEGAL_VECTOR_INDEX = index

    # What: 返回新索引。
    # Why: 调用方可能需要立刻使用索引信息。
    # How: 返回刚构建好的 index。
    return index


# What: 获取或构建法规向量索引。
# Why: 检索接口不应该关心索引是否已经存在。
# How: 如果缓存存在就直接返回，否则从数据库重建。
async def get_or_build_legal_vector_index(
    db: Session,
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> LegalVectorIndex:
    # What: 读取缓存索引。
    # Why: 如果已经构建过，就直接复用。
    # How: 调用 get_cached_legal_vector_index。
    cached_index = get_cached_legal_vector_index()

    # What: 判断缓存是否可用。
    # Why: 空索引没有检索价值，需要重新构建。
    # How: 缓存存在且 chunk_count 大于 0 就返回。
    if cached_index is not None and cached_index.chunk_count > 0:
        return cached_index

    # What: 缓存不可用时重建索引。
    # Why: 第一次启动或缓存清空后必须重新构建。
    # How: 调用 rebuild_legal_vector_index_from_db。
    return await rebuild_legal_vector_index_from_db(
        db,
        batch_size=batch_size,
    )