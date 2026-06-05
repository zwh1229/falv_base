from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import get_settings
# What: 引入问答上下文构建函数。
# Why: 风险分析需要把多轮回答整理成一段企业事实。
# How: 使用 build_audit_answer_context。
from app.services.audit_context_builder import build_audit_answer_context
from app.services.audit_report_builder import (
    build_audit_report_markdown,
    get_audit_report_pdf_path,
    save_audit_report_pdf_file,
    utc_now_iso,
)

# What: 引入法规索引管理函数。
# Why: 分析接口需要拿到向量索引和 BM25 索引。
# How: 复用缓存，避免每次重建。
from app.services.legal_index_manager import (
    get_or_build_legal_bm25_index,
    get_or_build_legal_vector_index,
)

# What: 引入 Hybrid 检索函数。
# Why: 风险分析前要先检索相关法规依据。
# How: 使用 search_legal_hybrid。
from app.services.legal_hybrid_retriever import search_legal_hybrid

# What: 引入风险分析函数。
# Why: 拿到企业事实和法规依据后，需要调用 56 Chat 生成分析。
# How: 使用 analyze_cross_border_risk。
from app.services.risk_analyzer import analyze_cross_border_risk


# What: 引入体检任务仓库函数。
# Why: 分析接口需要获取任务信息和该任务的全部问答。
# How: 从 audit_task_store.py 导入。
from app.repositories.audit_task_store import (
    create_audit_analysis_result,
    create_audit_task,
    get_audit_task,
    get_latest_audit_analysis_result,
    list_audit_answers_by_task_id,
    submit_audit_answer,
)

# What: 导入请求和响应模型。
# Why: 分析接口需要返回 AuditRiskAnalysisResponse。
# How: 从 app.schemas.audit 导入。
from app.schemas.audit import (
    AuditAnalysisEvidenceResponse,
    AuditReportResponse,
    AuditRiskAnalysisResponse,
    AuditTaskResponse,
    CreateAuditTaskRequest,
    SubmitAuditAnswerRequest,
)
# 创建体检任务路由对象
router = APIRouter(prefix="/audit-tasks", tags=["audit-tasks"])


# 创建体检任务接口
@router.post("", response_model=AuditTaskResponse, status_code=201)
def create_task(

    payload: CreateAuditTaskRequest,


    db: Session = Depends(get_db),
) -> AuditTaskResponse:

    return create_audit_task(db, payload)


# What: 查询体检任务接口
# Why: 前端需要根据 task_id 查看任务状态和当前问题
# How: GET /api/v1/audit-tasks/{task_id} 会调用这个函数
@router.get("/{task_id}", response_model=AuditTaskResponse)
def get_task(
    # What: 路径里的任务 ID
    # Why: 查询任务必须知道要查哪一个任务
    # How: FastAPI 会从 URL 里取出 task_id
    task_id: str,

    # What: 数据库会话
    # Why: 查询任务要访问 SQLite
    # How: Depends(get_db) 会自动注入 db
    db: Session = Depends(get_db),
) -> AuditTaskResponse:
    # What: 调用仓储层查询任务
    # Why: 数据库读取逻辑放在 repository 里
    # How: get_audit_task 会按 task_id 查 audit_tasks 表
    task = get_audit_task(db, task_id)


    if task is None:
        raise HTTPException(status_code=404, detail="audit task not found")


    return task


# 提交一轮回答接口
@router.post("/{task_id}/answers", response_model=AuditTaskResponse)
def submit_answer(

    task_id: str,

    # JSON 转成 SubmitAuditAnswerRequest
    payload: SubmitAuditAnswerRequest,

    db: Session = Depends(get_db),
) -> AuditTaskResponse:

    task = submit_audit_answer(db, task_id, payload)


    if task is None:
        raise HTTPException(status_code=404, detail="audit task not found")

#    AuditTaskResponse 转成 JSON
    return task




# What: 生成体检任务风险分析。
# Why: 用户完成问答后，需要基于企业事实和法规依据生成合规风险分析。
# How: 取任务 -> 取问答 -> Hybrid 检索 -> 调用 56 Chat -> 返回分析结果。
@router.post("/{task_id}/analysis", response_model=AuditRiskAnalysisResponse)
async def analyze_audit_task(
    task_id: str,
    db: Session = Depends(get_db),
) -> AuditRiskAnalysisResponse:
    # What: 查询体检任务。
    # Why: 不存在的任务不能分析。
    # How: 使用已有 get_audit_task。
    task = get_audit_task(db, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="audit task not found")

    # What: 查询该任务的全部回答。
    # Why: 风险分析必须基于用户多轮问答事实。
    # How: 按 round_no 升序读取 AuditAnswer。
    answers = list_audit_answers_by_task_id(db, task_id)

    # What: 构建企业问答上下文。
    # Why: 大模型需要一段连续的企业事实描述。
    # How: 使用 build_audit_answer_context。
    audit_context = build_audit_answer_context(answers)

    # What: 检查问答上下文是否为空。
    # Why: 没有企业事实时，分析结果没有依据。
    # How: 直接返回 400。
    if not audit_context.strip():
        raise HTTPException(status_code=400, detail="audit answers are empty")

    # What: 获取法规向量索引。
    # Why: Hybrid 检索需要语义召回。
    # How: 复用内存缓存，没有就自动构建。
    vector_index = await get_or_build_legal_vector_index(db)

    # What: 获取 BM25 索引。
    # Why: Hybrid 检索需要关键词召回。
    # How: 复用内存缓存，没有就自动构建。
    bm25_index = get_or_build_legal_bm25_index(db)

    # What: 执行 Hybrid 法规检索。
    # Why: 风险分析需要引用真实法规依据。
    # How: 用企业问答上下文作为 query，并按任务国家和数据跨境领域过滤。
    legal_hits = await search_legal_hybrid(
        vector_index=vector_index,
        bm25_index=bm25_index,
        query=audit_context,
        top_k=8,
        countries=task.countries,
        domains=["cross_border_data"],
    )

    # What: 调用风险分析模型。
    # Why: 需要结合企业事实和法规依据生成结构化合规分析。
    # How: 使用 analyze_cross_border_risk，当前走 56 Chat。
    analysis = await analyze_cross_border_risk(
        audit_context=audit_context,
        legal_hits=legal_hits,
    )

    # What: 构建法规依据落库 payload。
    # Why: 分析结果保存时，需要同时保存本次引用的法规依据。
    # How: 把 LegalHybridHit 转成 JSON 可保存的 dict。
    evidence_payload = [
        {
            "record_id": hit.chunk.record_id,
            "country": hit.chunk.country,
            "domain": hit.chunk.domain,
            "law_title": hit.chunk.law_title,
            "chunk_index": hit.chunk.chunk_index,
            "hybrid_score": hit.hybrid_score,
            "vector_score": hit.vector_score,
            "bm25_score": hit.bm25_score,
        }
        for hit in legal_hits
    ]

    # What: 保存风险分析结果。
    # Why: 分析结果不能只返回给前端，还要落库供后续报告使用。
    # How: 调用 create_audit_analysis_result 写入 audit_analysis_results 表。
    analysis_result = create_audit_analysis_result(
        db=db,
        task_id=task_id,
        audit_context=audit_context,
        analysis_text=analysis,
        evidences=evidence_payload,
        model_name=get_settings().chat_model,
        retrieval_method="hybrid",
    )

    # What: 返回分析结果。
    # Why: 前端需要展示分析正文和法规依据。
    # How: 把 legal_hits 转成响应 schema。
    return AuditRiskAnalysisResponse(
        task_id=task.task_id,
        analysis_id=analysis_result.analysis_id,
        model_name=analysis_result.model_name,
        retrieval_method=analysis_result.retrieval_method,
        created_at_utc=analysis_result.created_at_utc,
        company_name=task.company_name,
        scope=task.scope,
        countries=task.countries,
        audit_context=audit_context,
        evidences=[
            AuditAnalysisEvidenceResponse(
                record_id=hit.chunk.record_id,
                country=hit.chunk.country,
                domain=hit.chunk.domain,
                law_title=hit.chunk.law_title,
                chunk_index=hit.chunk.chunk_index,
                hybrid_score=hit.hybrid_score,
                vector_score=hit.vector_score,
                bm25_score=hit.bm25_score,
            )
            for hit in legal_hits
        ],
        analysis=analysis,
    )


# What: 查询体检任务最近一次风险分析结果。
# Why: 前端刷新页面或查看历史结果时，不应该重新调用大模型。
# How: 从 audit_analysis_results 表按 created_at_utc 倒序取最新一条。
@router.get("/{task_id}/analysis/latest", response_model=AuditRiskAnalysisResponse)
def get_latest_audit_task_analysis(
    task_id: str,
    db: Session = Depends(get_db),
) -> AuditRiskAnalysisResponse:
    # What: 查询体检任务。
    # Why: 不存在的任务不能查询分析结果。
    # How: 使用已有 get_audit_task。
    task = get_audit_task(db, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="audit task not found")

    # What: 查询最近一次分析结果。
    # Why: 一个任务可能被分析多次，默认返回最新结果。
    # How: 使用 get_latest_audit_analysis_result。
    analysis_result = get_latest_audit_analysis_result(db, task_id)

    if analysis_result is None:
        raise HTTPException(status_code=404, detail="audit analysis result not found")

    # What: 返回最近一次分析结果。
    # Why: 响应结构要和 POST /analysis 保持一致。
    # How: 把数据库里的 evidences JSON 转成响应 schema。
    return AuditRiskAnalysisResponse(
        task_id=task.task_id,
        analysis_id=analysis_result.analysis_id,
        model_name=analysis_result.model_name,
        retrieval_method=analysis_result.retrieval_method,
        created_at_utc=analysis_result.created_at_utc,
        company_name=task.company_name,
        scope=task.scope,
        countries=task.countries,
        audit_context=analysis_result.audit_context,
        evidences=[
            AuditAnalysisEvidenceResponse(**evidence)
            for evidence in analysis_result.evidences
        ],
        analysis=analysis_result.analysis_text,
    )


# What: 生成体检任务 Markdown 报告。
# Why: 前端和后续导出功能需要一个完整报告文本。
# How: 基于最近一次已落库的分析结果生成，不重新调用模型。
@router.get("/{task_id}/report", response_model=AuditReportResponse)
def get_audit_task_report(
    task_id: str,
    db: Session = Depends(get_db),
) -> AuditReportResponse:
    # What: 查询体检任务。
    # Why: 不存在的任务不能生成报告。
    # How: 使用已有 get_audit_task。
    task = get_audit_task(db, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="audit task not found")

    # What: 查询最近一次分析结果。
    # Why: 报告基于已保存的风险分析生成。
    # How: 使用 get_latest_audit_analysis_result。
    analysis_result = get_latest_audit_analysis_result(db, task_id)

    if analysis_result is None:
        raise HTTPException(status_code=404, detail="audit analysis result not found")

    # What: 生成报告时间。
    # Why: 报告响应需要记录本次报告生成时间。
    # How: 使用 UTC ISO 字符串。
    generated_at_utc = utc_now_iso()

    # What: 构建 Markdown 报告正文。
    # Why: Markdown 方便前端展示，也方便后续导出。
    # How: 使用 build_audit_report_markdown。
    report_text = build_audit_report_markdown(
        task=task,
        analysis_result=analysis_result,
        generated_at_utc=generated_at_utc,
    )

    # What: 返回报告响应。
    # Why: 前端需要报告正文和基础元数据。
    # How: 使用 AuditReportResponse。
    return AuditReportResponse(
        task_id=task.task_id,
        analysis_id=analysis_result.analysis_id,
        company_name=task.company_name,
        scope=task.scope,
        countries=task.countries,
        report_format="markdown",
        generated_at_utc=generated_at_utc,
        report_text=report_text,
    )


# What: 直接下载 PDF 报告文件。
# Why: 业务用户更适合查看和流转 PDF 报告。
# How: 基于最新分析结果重新拼装报告，再写入 backend/outputs/reports 后返回 FileResponse。
@router.get("/{task_id}/report/file")
def download_audit_task_report_file(
    task_id: str,
    db: Session = Depends(get_db),
):
    task = get_audit_task(db, task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="audit task not found")

    analysis_result = get_latest_audit_analysis_result(db, task_id)

    if analysis_result is None:
        raise HTTPException(status_code=404, detail="audit analysis result not found")

    report_path = get_audit_report_pdf_path(
        task_id=task.task_id,
        analysis_id=analysis_result.analysis_id,
    )

    if not report_path.exists():
        generated_at_utc = utc_now_iso()
        report_text = build_audit_report_markdown(
            task=task,
            analysis_result=analysis_result,
            generated_at_utc=generated_at_utc,
        )
        report_path = save_audit_report_pdf_file(
            task_id=task.task_id,
            analysis_id=analysis_result.analysis_id,
            report_text=report_text,
        )

    return FileResponse(
        path=report_path,
        filename=report_path.name,
        media_type="application/pdf",
    )
