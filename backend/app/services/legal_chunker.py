from dataclasses import dataclass
from app.models.legal import LegalRecord
from app.services.legal_content_reader import read_legal_content
from app.services.legal_text_cleaner import clean_legal_text
#定义chunk数据结构
@dataclass
class LegalChunk:
    #法规记录 ID。
    record_id: str

    #国家或地区。
    country: str

    #法规领域。
    domain: str

    #法规标题。
    law_title: str

    #序号。
    chunk_index: int

    #chunk 文本。
    text: str




DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 200


#切分chunk 优先段落拼接
def split_text_to_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:

    if not text.strip():
        return []

    paragraphs = [line.strip() for line in text.split("\n") if line.strip()]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_length = 0


    for paragraph in paragraphs:

        if len(paragraph) > chunk_size:
            if current_parts:
                chunks.append("\n".join(current_parts))
                current_parts = []
                current_length = 0

            start = 0
            step = chunk_size - chunk_overlap

            while start < len(paragraph):
                end = start + chunk_size
                chunk = paragraph[start:end].strip()

                if chunk:
                    chunks.append(chunk)

                start += step

            continue

        next_length = current_length + len(paragraph) + 1

        if current_parts and next_length > chunk_size:
            current_text = "\n".join(current_parts)
            chunks.append(current_text)


            overlap_text = current_text[-chunk_overlap:].strip()

            current_parts = [overlap_text] if overlap_text else []
            current_length = len(overlap_text)


        current_parts.append(paragraph)
        current_length += len(paragraph) + 1

    if current_parts:
        chunks.append("\n".join(current_parts))


    return [chunk for chunk in chunks if chunk.strip()]






# What: 获取法规标题。
# Why: 检索结果和后续报告里要展示法规名称。
# How: 优先用本地标题，没有就用英文标题，再没有就用 record_id。
def get_legal_record_title(record: LegalRecord) -> str:
    # What: 判断本地语言标题是否存在。
    # Why: 中国法规、越南法规通常本地标题更适合展示。
    # How: 先判断不为空，再去掉前后空格。
    if record.law_title_local and record.law_title_local.strip():
        # What: 返回本地语言标题。
        # Why: 这是优先级最高的法规标题。
        # How: strip 去掉多余空格。
        return record.law_title_local.strip()

    # What: 判断英文标题是否存在。
    # Why: 新加坡法规或英文资料可能主要靠英文标题展示。
    # How: 先判断不为空，再去掉前后空格。
    if record.law_title_en and record.law_title_en.strip():
        # What: 返回英文标题。
        # Why: 本地标题没有时，用英文标题兜底。
        # How: strip 去掉多余空格。
        return record.law_title_en.strip()

    # What: 返回法规记录 ID。
    # Why: 如果两个标题都没有，至少还要能追踪来源。
    # How: 直接用 record_id 作为兜底标题。
    return record.record_id


# What: 把一条法规记录构造成多个 LegalChunk。
# Why: embedding、BM25、hybrid 检索都不是直接检索整篇法规，而是检索 chunk。
# How: 读取正文 -> 清洗正文 -> 切块 -> 封装成 LegalChunk 列表。
def build_legal_chunks(record: LegalRecord) -> list[LegalChunk]:
    # What: 读取法规原始正文。
    # Why: LegalRecord 里只存 content_path，不直接存正文内容。
    # How: read_legal_content 会根据 record.content_path 读取文件。
    raw_text = read_legal_content(record.content_path)

    # What: 清洗法规正文。
    # Why: 原始正文可能包含 HTML、导航、脚本、空行等噪声。
    # How: clean_legal_text 会输出适合切块的纯文本。
    cleaned_text = clean_legal_text(raw_text)

    # What: 把清洗后的正文切成多个文本块。
    # Why: 长法规不能整篇送去 embedding，必须拆成稳定大小的 chunk。
    # How: split_text_to_chunks 默认按 1200 字左右切，保留 200 字重叠。
    chunk_texts = split_text_to_chunks(cleaned_text)

    # What: 获取法规标题。
    # Why: 每个 chunk 都要带上法规标题，方便后续展示和引用。
    # How: 使用 get_legal_record_title 做统一兜底。
    law_title = get_legal_record_title(record)

    # What: 创建最终 chunk 列表。
    # Why: 后续检索模块需要结构化的 chunk，而不是纯字符串列表。
    # How: enumerate 给每个 chunk 生成序号。
    return [
        # What: 创建一个法规 chunk。
        # Why: 每个 chunk 都要保留来源、领域、标题和正文。
        # How: 从 record 取元数据，从 chunk_texts 取正文。
        LegalChunk(
            record_id=record.record_id,
            country=record.country,
            domain=record.domain,
            law_title=law_title,
            chunk_index=index,
            text=chunk_text,
        )
        # What: 遍历所有 chunk 文本。
        # Why: 一条法规会被切成多个 chunk。
        # How: index 是序号，chunk_text 是正文片段。
        for index, chunk_text in enumerate(chunk_texts)
    ]



def build_many_legal_chunks(records: list[LegalRecord]) -> list[LegalChunk]:
    # What: 创建一个空的 chunk 总列表。
    # Why: 所有法规记录生成的 chunk 都要汇总到这里。
    # How: 用 list 保存 LegalChunk 对象。
    all_chunks: list[LegalChunk] = []

    # What: 遍历每一条法规记录。
    # Why: 每条法规都有自己的 content_path，需要单独读取、清洗、切块。
    # How: records 是 LegalRecord 列表，逐条处理。
    for record in records:
        # What: 构建当前法规记录的 chunks。
        # Why: build_legal_chunks 已经封装了读取、清洗、切块逻辑。
        # How: 把当前 record 传进去，返回当前法规的 chunk 列表。
        record_chunks = build_legal_chunks(record)

        # What: 把当前法规的 chunks 合并到总列表。
        # Why: 后面 embedding 需要统一处理所有 chunk。
        # How: extend 会把一个列表里的元素追加进 all_chunks。
        all_chunks.extend(record_chunks)

    # What: 返回所有法规 chunks。
    # Why: 后续向量化和检索模块都要用这个结果。
    # How: 返回 list[LegalChunk]。
    return all_chunks


