# What: 引入 dataclass。
# Why: 向量索引里的对象只是内存结构，不需要写成数据库模型。
# How: 用 @dataclass 自动生成初始化方法。
from dataclasses import dataclass

# What: 引入时间工具。
# Why: 后面索引构建完成后，需要记录 built_at_utc。
# How: 使用 timezone.utc 保证时间统一。
from datetime import datetime, timezone

# What: 引入数学工具。
# Why: 向量归一化时需要计算平方根。
# How: 使用 math.sqrt。
import math

# What: 引入法规 chunk 结构。
# Why: 每个向量都必须绑定一个法规 chunk，方便追溯来源。
# How: 从 legal_chunker.py 导入 LegalChunk。
from app.services.legal_chunker import LegalChunk
from app.services.embedding_client import async_embed_texts

# What: 默认 embedding 批大小。
# Why: 后面批量调用 embedding 时，不能一次塞太多文本。
# How: 先用 16，兼顾速度和稳定性。
DEFAULT_EMBEDDING_BATCH_SIZE = 16

# What: 默认向量检索返回数量。
# Why: 后面不能把太多法规片段都丢给大模型。
# How: 默认返回 top 8。
DEFAULT_VECTOR_TOP_K = 8


# What: 定义向量索引中的单条数据。
# Why: 一个 chunk embedding 后，需要把 chunk 和 vector 绑在一起。
# How: chunk 保存法规来源，vector 保存归一化后的向量。
@dataclass
class LegalVectorItem:
    # What: 法规 chunk。
    # Why: 检索命中后，需要知道命中了哪条法规的哪一段。
    # How: 使用 LegalChunk 保存 record_id、country、domain、law_title、text。
    chunk: LegalChunk

    # What: chunk 的向量。
    # Why: 检索时要用它和 query 向量计算相似度。
    # How: 保存归一化后的 list[float]。
    vector: list[float]


# What: 定义向量检索命中结果。
# Why: 检索结果不只需要 chunk，还需要分数。
# How: chunk 是命中的法规片段，score 是相似度。
@dataclass
class LegalVectorHit:
    # What: 命中的法规 chunk。
    # Why: 后面风险分析要引用这段法规。
    # How: 使用 LegalChunk 保存完整来源信息。
    chunk: LegalChunk

    # What: 相似度分数。
    # Why: 分数越高，说明 query 和法规片段越相关。
    # How: 使用归一化向量点积计算。
    score: float


# What: 定义完整的法规向量索引。
# Why: 后面检索时，需要统一管理所有向量条目。
# How: items 保存向量条目，dimension 保存维度，built_at_utc 保存构建时间。
@dataclass
class LegalVectorIndex:
    # What: 向量条目列表。
    # Why: 每个条目代表一个可以被检索的法规 chunk。
    # How: 使用 list[LegalVectorItem] 保存。
    items: list[LegalVectorItem]

    # What: 向量维度。
    # Why: query 向量和法规向量必须维度一致。
    # How: ada-002 正常返回 1536 维。
    dimension: int

    # What: 索引构建时间。
    # Why: 后面可以判断索引是不是过期。
    # How: 保存 UTC ISO 字符串。
    built_at_utc: str

    # What: 返回索引里的 chunk 数量。
    # Why: 调试、接口返回、日志里都要看到索引规模。
    # How: 直接返回 items 的长度。
    @property
    def chunk_count(self) -> int:
        return len(self.items)


# What: 获取当前 UTC 时间。
# Why: 构建索引时要记录统一时间。
# How: datetime.now(timezone.utc).isoformat()。
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# What: 计算向量的 L2 模长。
# Why: 向量归一化需要除以模长。
# How: 每个元素平方求和后开平方。
def l2_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


# What: 归一化向量。
# Why: 归一化后，余弦相似度可以直接用点积计算。
# How: 每个元素除以向量 L2 模长。
def normalize_vector(vector: list[float]) -> list[float]:
    norm = l2_norm(vector)

    if norm == 0:
        return []

    return [value / norm for value in vector]


# What: 计算两个向量点积。
# Why: 对归一化向量来说，点积就是余弦相似度。
# How: 两个向量同位置元素相乘后求和。
def dot_product(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0

    if len(left) != len(right):
        return 0.0

    return sum(
        left_value * right_value
        for left_value, right_value in zip(left, right)
    )


# What: 把 chunk 列表切成批次。
# Why: 后面调用 embedding 接口时，需要分批发送。
# How: 每 batch_size 个 chunk 组成一批。
def batch_chunks(
    chunks: list[LegalChunk],
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> list[list[LegalChunk]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than 0")

    return [
        chunks[start : start + batch_size]
        for start in range(0, len(chunks), batch_size)
    ]


# What: 构建法规向量索引。
# Why: 检索不能每次都重新 embedding 全部法规，必须先把法规 chunks 建成索引。
# How: 分批 embedding -> 检查向量维度 -> 归一化 -> 封装成 LegalVectorIndex。
async def build_legal_vector_index(
    chunks: list[LegalChunk],
    batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE,
) -> LegalVectorIndex:
    # What: 处理空 chunk 列表。
    # Why: 没有法规 chunk 时，也要返回一个合法的空索引，避免上层报错。
    # How: items 为空，dimension 为 0，记录构建时间。
    if not chunks:
        return LegalVectorIndex(
            items=[],
            dimension=0,
            built_at_utc=utc_now_iso(),
        )

    # What: 创建索引条目列表。
    # Why: 每个 LegalVectorItem 都代表一个可检索的法规 chunk。
    # How: 后面逐批 append。
    index_items: list[LegalVectorItem] = []

    # What: 初始化向量维度。
    # Why: 第一条 embedding 出来后，用它确定统一维度。
    # How: 初始为 0，第一次拿到 vector 后赋值。
    vector_dimension = 0

    # What: 把 chunks 分批处理。
    # Why: embedding 接口一次请求太多文本可能超时。
    # How: 使用 batch_chunks 按 batch_size 切分。
    for chunk_batch in batch_chunks(chunks, batch_size):
        # What: 提取当前批次的文本。
        # Why: embedding 接口只接收文本列表，不接收 LegalChunk 对象。
        # How: 从每个 chunk 中取 text。
        texts = [chunk.text for chunk in chunk_batch]

        # What: 调用 embedding 接口。
        # Why: 需要把法规文本转成向量。
        # How: await async_embed_texts(texts) 返回 list[list[float]]。
        vectors = await async_embed_texts(texts)

        # What: 检查 embedding 返回数量。
        # Why: 返回向量数量必须和输入 chunk 数量一致。
        # How: 不一致就抛异常，避免索引错位。
        if len(vectors) != len(chunk_batch):
            raise RuntimeError("Embedding result count does not match chunk count")

        # What: 遍历当前批次的 chunk 和 vector。
        # Why: 要把每个 chunk 和自己的 embedding 绑定起来。
        # How: 使用 zip 一一配对。
        for chunk, vector in zip(chunk_batch, vectors):
            # What: 跳过空向量。
            # Why: 空向量无法参与检索。
            # How: 如果 vector 为空，直接 continue。
            if not vector:
                continue

            # What: 初始化向量维度。
            # Why: 第一条有效向量决定整个索引的维度。
            # How: vector_dimension 为 0 时赋值。
            if vector_dimension == 0:
                vector_dimension = len(vector)

            # What: 检查向量维度一致性。
            # Why: 同一个索引里的向量必须维度相同。
            # How: 维度不一致就抛异常。
            if len(vector) != vector_dimension:
                raise RuntimeError("Embedding vector dimension is inconsistent")

            # What: 归一化向量。
            # Why: 后面检索时可以直接用点积算余弦相似度。
            # How: 调用 normalize_vector。
            normalized_vector = normalize_vector(vector)

            # What: 跳过归一化失败的向量。
            # Why: 零向量归一化后为空，不能检索。
            # How: normalized_vector 为空时 continue。
            if not normalized_vector:
                continue

            # What: 添加一个向量索引条目。
            # Why: 这个条目就是后面可以被检索的一段法规。
            # How: chunk 保存来源，vector 保存归一化向量。
            index_items.append(
                LegalVectorItem(
                    chunk=chunk,
                    vector=normalized_vector,
                )
            )

    # What: 返回完整法规向量索引。
    # Why: 后续 query 检索会基于这个索引做 top-k。
    # How: 封装 items、dimension、built_at_utc。
    return LegalVectorIndex(
        items=index_items,
        dimension=vector_dimension,
        built_at_utc=utc_now_iso(),
    )



# What: 判断一个向量条目是否满足过滤条件。
# Why: 检索时可能只想查某些国家或某些法规领域。
# How: countries 和 domains 为空就不过滤，不为空就做集合匹配。
def matches_filters(
    item: LegalVectorItem,
    countries: list[str] | None = None,
    domains: list[str] | None = None,
) -> bool:
    # What: 判断国家过滤条件。
    # Why: 例如中国数据出境问题，优先只查 China。
    # How: 如果 countries 有值，但 item 国家不在里面，就过滤掉。
    if countries and item.chunk.country not in set(countries):
        return False

    # What: 判断法规领域过滤条件。
    # Why: 例如数据跨境问题，优先只查 cross_border_data。
    # How: 如果 domains 有值，但 item 领域不在里面，就过滤掉。
    if domains and item.chunk.domain not in set(domains):
        return False

    # What: 返回通过过滤。
    # Why: 走到这里说明没有被国家或领域条件排除。
    # How: 返回 True。
    return True


# What: 搜索法规向量索引。
# Why: 风险分析前，需要先找出和企业事实最相关的法规 chunk。
# How: query embedding -> 归一化 -> 和索引向量算点积 -> 排序取 top-k。
async def search_legal_vector_index(
    index: LegalVectorIndex,
    query: str,
    top_k: int = DEFAULT_VECTOR_TOP_K,
    countries: list[str] | None = None,
    domains: list[str] | None = None,
    min_score: float | None = None,
) -> list[LegalVectorHit]:
    # What: 处理无效 top_k。
    # Why: top_k 小于等于 0 时没有检索意义。
    # How: 直接返回空列表。
    if top_k <= 0:
        return []

    # What: 处理空 query。
    # Why: 空问题不能做 embedding 检索。
    # How: 去掉空格后为空就返回空列表。
    if not query.strip():
        return []

    # What: 处理空索引。
    # Why: 没有法规向量时无法检索。
    # How: index.items 为空就返回空列表。
    if not index.items:
        return []

    # What: 把 query 转成 embedding。
    # Why: 向量检索必须比较 query 向量和 chunk 向量。
    # How: 调用 async_embed_texts，输入单条 query。
    query_vectors = await async_embed_texts([query])

    # What: 检查 query embedding 是否返回。
    # Why: embedding 接口异常时可能没有有效结果。
    # How: 没有结果就返回空列表。
    if not query_vectors:
        return []

    # What: 取出 query 向量。
    # Why: async_embed_texts 返回的是列表，这里只查一个 query。
    # How: 使用 query_vectors[0]。
    query_vector = query_vectors[0]

    # What: 检查 query 向量维度。
    # Why: query 向量维度必须和索引维度一致。
    # How: 不一致就抛异常，避免错误检索。
    if len(query_vector) != index.dimension:
        raise RuntimeError("Query vector dimension does not match index dimension")

    # What: 归一化 query 向量。
    # Why: 归一化后可以直接用点积计算余弦相似度。
    # How: 调用 normalize_vector。
    normalized_query_vector = normalize_vector(query_vector)

    # What: 处理归一化失败。
    # Why: 零向量不能用于检索。
    # How: 返回空列表。
    if not normalized_query_vector:
        return []

    # What: 创建命中结果列表。
    # Why: 每个通过过滤的 chunk 都会生成一个候选 hit。
    # How: 使用 list[LegalVectorHit] 保存。
    hits: list[LegalVectorHit] = []

    # What: 遍历索引里的所有向量条目。
    # Why: 当前数据量小，直接全量精确计算最稳。
    # How: 逐条计算 query 和 chunk 的相似度。
    for item in index.items:
        # What: 应用国家和领域过滤。
        # Why: 可以减少无关法规参与排序。
        # How: 不满足过滤条件就跳过。
        if not matches_filters(item, countries=countries, domains=domains):
            continue

        # What: 计算向量相似度。
        # Why: 分数越高，说明法规 chunk 和 query 越相关。
        # How: 归一化向量点积。
        score = dot_product(normalized_query_vector, item.vector)

        # What: 应用最低分过滤。
        # Why: 可以过滤明显不相关的低分结果。
        # How: min_score 不为空且 score 更低时跳过。
        if min_score is not None and score < min_score:
            continue

        # What: 添加检索命中结果。
        # Why: 后面要排序并返回 top-k。
        # How: 保存 chunk 和 score。
        hits.append(
            LegalVectorHit(
                chunk=item.chunk,
                score=score,
            )
        )

    # What: 按相似度从高到低排序。
    # Why: 最相关的法规 chunk 应该排在前面。
    # How: 使用 score 作为排序 key。
    hits.sort(key=lambda hit: hit.score, reverse=True)

    # What: 返回 top-k 结果。
    # Why: 后续大模型只需要看最相关的一批法规依据。
    # How: 切片返回前 top_k 条。
    return hits[:top_k]