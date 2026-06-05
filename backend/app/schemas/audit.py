from enum import Enum
from typing import Optional
from pydantic import BaseModel



#定义体检任务的审查范围
class AuditScope(str, Enum):
    china = 'china'
    #中新
    china_singapore = 'china_singapore'
    #中越
    china_vietnam = 'china_vietnam'


#定义创建任务时的数据格式

class CreateAuditTaskRequest(BaseModel):
    #企业名称
    company_name: Optional[str] = None
    #审查范围
    scope: AuditScope


#定义后端给前端返回的数据格式
class AuditTaskResponse(BaseModel):
    #任务id
    task_id: str

    
    company_name: Optional[str] = None

    # AuditScope，保证返回值也固定。
    scope: AuditScope

    #  scope 转成 ["China", "Singapore"] 这种列表。
    countries: list[str]

  
    #第一版先用字符串，后面需要时再改成枚举。
    status: str

    
    #暂定 5 轮问答，后端要知道现在到第几轮。
    #任务创建时是 1，每提交一轮回答就加 1。
    current_round: int
    #下一轮要问的问题
    next_question: Optional[str] = None 


# 提交问题模型 
class SubmitAuditAnswerRequest(BaseModel):

    answer: str


class AuditAnswerResponse(BaseModel):
    id: int
    task_id: str
    round_no: int
    answer: str



# What: 定义风险分析命中的法规依据响应。
# Why: 前端和调试时需要知道本次分析用了哪些法规片段。
# How: 从 LegalHybridHit 里提取法规来源和分数。
class AuditAnalysisEvidenceResponse(BaseModel):
    # What: 法规记录 ID。
    # Why: 风险分析结论必须能追溯到具体法规。
    # How: 来自 hit.chunk.record_id。
    record_id: str

    # What: 国家或地区。
    # Why: 展示该依据属于哪个法域。
    # How: 来自 hit.chunk.country。
    country: str

    # What: 法规领域。
    # Why: 展示该依据属于数据跨境、税务还是雇佣等领域。
    # How: 来自 hit.chunk.domain。
    domain: str

    # What: 法规标题。
    # Why: 用户不能只看法规 ID。
    # How: 来自 hit.chunk.law_title。
    law_title: str

    # What: chunk 序号。
    # Why: 同一条法规会切成多段，需要知道命中哪一段。
    # How: 来自 hit.chunk.chunk_index。
    chunk_index: int

    # What: Hybrid 融合分。
    # Why: 表示该依据的综合相关性。
    # How: 来自 hit.hybrid_score。
    hybrid_score: float

    # What: 向量相似度分。
    # Why: 用于调试语义召回贡献。
    # How: 来自 hit.vector_score。
    vector_score: float

    # What: BM25 关键词分。
    # Why: 用于调试关键词召回贡献。
    # How: 来自 hit.bm25_score。
    bm25_score: float


# What: 定义体检任务风险分析响应。
# Why: /audit-tasks/{task_id}/analysis 需要返回完整分析结果。
# How: 包含任务 ID、上下文、法规依据和模型分析文本。
class AuditRiskAnalysisResponse(BaseModel):
    # What: 体检任务 ID。
    # Why: 调用方需要知道这是哪个任务的分析结果。
    # How: 来自 URL path 里的 task_id。
    task_id: str

    # What: 分析结果 ID。
    # Why: 分析结果已经落库，前端后续查询报告时需要这个 ID。
    # How: 来自 AuditAnalysisResult.analysis_id。
    analysis_id: str

    # What: 使用的模型名称。
    # Why: 后续排查和报告记录要知道本次分析用的哪个模型。
    # How: 当前来自配置里的 chat_model。
    model_name: str | None = None

    # What: 检索方法。
    # Why: 说明本次分析的法规依据来自哪种检索策略。
    # How: 当前固定为 hybrid。
    retrieval_method: str

    # What: 分析生成时间。
    # Why: 前端和报告需要展示分析时间。
    # How: 来自 AuditAnalysisResult.created_at_utc。
    created_at_utc: str

    # What: 企业名称。
    # Why: 报告和展示时需要企业主体信息。
    # How: 来自 AuditTaskResponse.company_name。
    company_name: str | None = None

    # What: 审查范围。
    # Why: 说明本次分析属于哪个跨境场景。
    # How: 来自 AuditTaskResponse.scope。
    scope: AuditScope

    # What: 涉及国家或地区。
    # Why: 法规检索会基于这些国家过滤。
    # How: 来自 AuditTaskResponse.countries。
    countries: list[str]

    # What: 企业问答上下文。
    # Why: 风险分析是基于用户多轮回答生成的。
    # How: 来自 build_audit_answer_context。
    audit_context: str

    # What: 法规依据列表。
    # Why: 用户需要知道模型参考了哪些法规。
    # How: 从 Hybrid hits 转换而来。
    evidences: list[AuditAnalysisEvidenceResponse]

    # What: 风险分析正文。
    # Why: 这是接口的核心输出。
    # How: 来自 analyze_cross_border_risk。
    analysis: str


# What: 定义体检报告响应。
# Why: 报告接口需要返回可展示的报告正文和基础元数据。
# How: report_text 使用 Markdown 文本，后续可以导出 PDF 或 Word。
class AuditReportResponse(BaseModel):
    # What: 体检任务 ID。
    # Why: 前端需要知道报告属于哪个任务。
    # How: 来自 AuditTaskResponse.task_id。
    task_id: str

    # What: 分析结果 ID。
    # Why: 报告基于某次已经落库的分析结果生成。
    # How: 来自 AuditAnalysisResult.analysis_id。
    analysis_id: str

    # What: 企业名称。
    # Why: 报告首页需要展示企业主体。
    # How: 来自 AuditTaskResponse.company_name。
    company_name: str | None = None

    # What: 审查范围。
    # Why: 报告需要说明分析的是哪个跨境范围。
    # How: 来自 AuditTaskResponse.scope。
    scope: AuditScope

    # What: 涉及国家或地区。
    # Why: 报告需要展示适用法域。
    # How: 来自 AuditTaskResponse.countries。
    countries: list[str]

    # What: 报告格式。
    # Why: 前端需要知道 report_text 当前是 Markdown。
    # How: MVP 阶段固定为 markdown。
    report_format: str = "markdown"

    # What: 报告生成时间。
    # Why: 用户需要知道报告是什么时候生成的。
    # How: 使用 UTC ISO 字符串。
    generated_at_utc: str

    # What: 报告正文。
    # Why: 这是报告接口的核心输出。
    # How: Markdown 文本，包含企业事实、法规依据和风险分析。
    report_text: str
