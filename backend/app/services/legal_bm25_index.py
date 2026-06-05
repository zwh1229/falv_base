# What: 引入 dataclass。
# Why: BM25 索引和命中结果也是内存结构。
# How: 使用 @dataclass 自动生成初始化方法。
from dataclasses import dataclass

# What: 引入正则工具。
# Why: 分词前需要提取英文、数字、中文片段。
# How: 使用 re.findall 做基础 token 兜底。
import re

# What: 引入 jieba 中文分词。
# Why: BM25 需要词粒度，中文不能只按空格切。
# How: jieba.lcut 把中文句子切成词。
import jieba

# What: 引入 BM25Okapi。
# Why: 它负责计算关键词相关性分数。
# How: rank-bm25 提供经典 BM25 实现。
from rank_bm25 import BM25Okapi

# What: 引入法规 chunk 结构。
# Why: BM25 索引里的每个文档也对应一个 LegalChunk。
# How: 复用 legal_chunker.py 里的 LegalChunk。
from app.services.legal_chunker import LegalChunk


# What: 默认 BM25 返回数量。
# Why: 不应该把所有 chunk 都作为关键词命中返回。
# How: 默认返回 top 8。
DEFAULT_BM25_TOP_K = 8

# What: 中文、英文、数字 token 匹配规则。
# Why: jieba 对英文数字有时不够稳定，需要正则兜底。
# How: 匹配连续中文、连续英文、连续数字。
TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]+|[a-zA-Z]+|\d+")


# What: 定义 BM25 检索命中结果。
# Why: 检索结果需要同时返回 chunk 和 BM25 分数。
# How: chunk 保存法规片段，score 保存关键词相关性。
@dataclass
class LegalBM25Hit:
    # What: 命中的法规 chunk。
    # Why: 后续 hybrid 融合和风险分析都要用法规来源。
    # How: 使用 LegalChunk 保存。
    chunk: LegalChunk

    # What: BM25 分数。
    # Why: 分数越高，说明关键词匹配越强。
    # How: 来自 BM25Okapi.get_scores。
    score: float


# What: 定义 BM25 索引。
# Why: 需要保存 chunks、分词后的语料和 BM25 对象。
# How: chunks 用于回溯来源，tokenized_corpus 用于调试，bm25 用于打分。
@dataclass
class LegalBM25Index:
    # What: 法规 chunks。
    # Why: BM25 返回的是位置，需要用 chunks 找回原始法规片段。
    # How: 和 tokenized_corpus 保持同顺序。
    chunks: list[LegalChunk]

    # What: 分词后的语料。
    # Why: BM25Okapi 用它建关键词索引。
    # How: 每个 chunk 对应一个 token list。
    tokenized_corpus: list[list[str]]

    # What: BM25 模型对象。
    # Why: 搜索时用它计算 query 和每个 chunk 的关键词相关分。
    # How: BM25Okapi(tokenized_corpus) 创建。
    bm25: BM25Okapi

    # What: 返回索引 chunk 数量。
    # Why: 调试和 API 返回时需要看索引规模。
    # How: 直接返回 chunks 长度。
    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


# What: 标准化 token。
# Why: 英文大小写、空格会影响 BM25 匹配。
# How: 去空格并转小写。
def normalize_token(token: str) -> str:
    return token.strip().lower()


# What: 判断 token 是否有效。
# Why: 空 token 和单个无意义符号不应该进入 BM25。
# How: 去空格后还有内容就保留。
def is_valid_token(token: str) -> bool:
    return bool(token.strip())


# What: 对文本进行分词。
# Why: BM25 需要把法规正文和查询都转成 token 列表。
# How: jieba 分词 + 正则兜底 + 统一小写。
def tokenize_text(text: str) -> list[str]:
    # What: 用 jieba 做中文分词。
    # Why: 中文法规文本没有自然空格，需要分词。
    # How: jieba.lcut 返回 token 列表。
    jieba_tokens = jieba.lcut(text)

    # What: 用正则做兜底 token 提取。
    # Why: 法规里有英文缩写、数字、条款号，正则能补一部分。
    # How: TOKEN_PATTERN.findall 提取中文、英文、数字片段。
    regex_tokens = TOKEN_PATTERN.findall(text)

    # What: 合并两种 token。
    # Why: jieba 负责语义词，正则负责硬匹配兜底。
    # How: 直接拼接列表。
    raw_tokens = jieba_tokens + regex_tokens

    # What: 标准化并过滤 token。
    # Why: 保证 BM25 语料干净。
    # How: normalize_token 后过滤空 token。
    return [
        normalized_token
        for token in raw_tokens
        if is_valid_token(token)
        for normalized_token in [normalize_token(token)]
        if is_valid_token(normalized_token)
    ]


# What: 构建 BM25 索引。
# Why: 关键词检索不能每次都重新分词和建模。
# How: chunks -> tokenized_corpus -> BM25Okapi。
def build_legal_bm25_index(chunks: list[LegalChunk]) -> LegalBM25Index:
    # What: 对每个 chunk 文本分词。
    # Why: BM25Okapi 需要 list[list[str]] 格式语料。
    # How: 调用 tokenize_text。
    tokenized_corpus = [
        tokenize_text(chunk.text)
        for chunk in chunks
    ]

    # What: 创建 BM25 模型。
    # Why: 后续搜索要用 BM25 分数排序。
    # How: BM25Okapi 接收分词后的语料。
    bm25 = BM25Okapi(tokenized_corpus)

    # What: 返回 BM25 索引结构。
    # Why: 后续 hybrid 检索要复用它。
    # How: 保存 chunks、tokenized_corpus、bm25。
    return LegalBM25Index(
        chunks=chunks,
        tokenized_corpus=tokenized_corpus,
        bm25=bm25,
    )


# What: 判断 chunk 是否满足过滤条件。
# Why: BM25 检索也要支持国家和法规领域过滤。
# How: countries/domains 为空不过滤，不为空就集合匹配。
def matches_bm25_filters(
    chunk: LegalChunk,
    countries: list[str] | None = None,
    domains: list[str] | None = None,
) -> bool:
    if countries and chunk.country not in set(countries):
        return False

    if domains and chunk.domain not in set(domains):
        return False

    return True


# What: 搜索 BM25 索引。
# Why: 根据关键词找到最匹配的法规 chunks。
# How: query 分词 -> BM25 打分 -> 过滤 -> 排序 -> top-k。
def search_legal_bm25_index(
    index: LegalBM25Index,
    query: str,
    top_k: int = DEFAULT_BM25_TOP_K,
    countries: list[str] | None = None,
    domains: list[str] | None = None,
    min_score: float | None = None,
) -> list[LegalBM25Hit]:
    # What: 处理无效 top_k。
    # Why: top_k 小于等于 0 没有检索意义。
    # How: 直接返回空列表。
    if top_k <= 0:
        return []

    # What: 处理空 query。
    # Why: 空查询无法做关键词召回。
    # How: 去空格后为空就返回空列表。
    if not query.strip():
        return []

    # What: 处理空索引。
    # Why: 没有 chunk 就没有可检索内容。
    # How: chunks 为空返回空列表。
    if not index.chunks:
        return []

    # What: 对 query 分词。
    # Why: BM25 查询也需要 token 列表。
    # How: 调用 tokenize_text。
    query_tokens = tokenize_text(query)

    # What: 处理空 query token。
    # Why: 没有 token 无法计算关键词相关性。
    # How: 返回空列表。
    if not query_tokens:
        return []

    # What: 计算 query 对每个 chunk 的 BM25 分数。
    # Why: 这是关键词相关性的核心。
    # How: BM25Okapi.get_scores 返回分数数组。
    scores = index.bm25.get_scores(query_tokens)

    # What: 创建命中结果列表。
    # Why: 要过滤、排序后返回。
    # How: 遍历 chunks 和 scores。
    hits: list[LegalBM25Hit] = []

    # What: 遍历每个 chunk 及其分数。
    # Why: BM25 分数数组和 chunks 顺序一致。
    # How: zip(index.chunks, scores) 一一对应。
    for chunk, score in zip(index.chunks, scores):
        # What: 应用过滤条件。
        # Why: 只保留目标国家和领域内的法规。
        # How: 不满足条件就跳过。
        if not matches_bm25_filters(chunk, countries=countries, domains=domains):
            continue

        # What: 转成 Python float。
        # Why: get_scores 可能返回 numpy 数值，响应和融合时用 float 更稳。
        # How: float(score)。
        score_value = float(score)

        # What: 应用最低分过滤。
        # Why: 可以排除没有关键词命中的 chunk。
        # How: min_score 不为空且分数低于阈值就跳过。
        if min_score is not None and score_value < min_score:
            continue

        # What: 添加 BM25 命中。
        # Why: 后面要排序取 top-k。
        # How: 保存 chunk 和 score。
        hits.append(
            LegalBM25Hit(
                chunk=chunk,
                score=score_value,
            )
        )

    # What: 按 BM25 分数从高到低排序。
    # Why: 关键词匹配最强的结果排前面。
    # How: 使用 score 作为排序 key。
    hits.sort(key=lambda hit: hit.score, reverse=True)

    # What: 返回 top-k。
    # Why: 后续 hybrid 只需要一批候选。
    # How: 切片取前 top_k 条。
    return hits[:top_k]