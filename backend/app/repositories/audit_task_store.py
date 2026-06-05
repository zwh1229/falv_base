from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.audit import AuditAnswer, AuditTask
# What: 引入体检任务、问答、分析结果模型。
# Why: 仓库层需要读写任务、回答和分析结果。
# How: 从 app.models.audit 导入三个 ORM 模型。
from app.models.audit import AuditAnalysisResult, AuditAnswer, AuditTask
from datetime import datetime, timezone

#CreateAuditTaskRequest 用于创建任务，AuditTaskResponse 用于返回任务，SubmitAuditAnswerRequest 用于提交回答 AuditAnswerResponse 回复回答
from app.schemas.audit import (
    AuditTaskResponse,
    AuditAnswerResponse,
    CreateAuditTaskRequest,
    SubmitAuditAnswerRequest,
)

#转换格式
from app.services.audit_scope import get_countries_by_scope

#获得第一轮问题 
from app.services.audit_question import get_question_by_round


#数据库转换成json
def to_audit_task_response(task: AuditTask) -> AuditTaskResponse:

    return AuditTaskResponse(
        task_id=task.task_id,
        company_name=task.company_name,
        scope=task.scope,
        countries=task.countries,
        status=task.status,
        current_round=task.current_round,
        next_question=task.next_question,
    )



def create_audit_task(
    db: Session,
    payload: CreateAuditTaskRequest,
) -> AuditTaskResponse:

    task_id = str(uuid4())

    # 拿国家列表
    countries = get_countries_by_scope(payload.scope)

    # 创建任务对象
    task = AuditTask(
        task_id=task_id,
        company_name=payload.company_name,
        scope=payload.scope.value,
        countries=countries,
        status="questioning",
        current_round=1,
        next_question=get_question_by_round(1),
    )


    db.add(task)


    db.commit()


    db.refresh(task)

    return to_audit_task_response(task)



#  db.get(AuditTask, task_id) 会按主键查 audit_tasks 表
def get_audit_task(
    db: Session,
    task_id: str,
) -> AuditTaskResponse | None:

    task = db.get(AuditTask, task_id)
    # 任务不存在就是NONE
    if task is None:
        return None

    #转换
    return to_audit_task_response(task)



#  写入 audit_answers 表，然后更新 audit_tasks 表的 current_round 和 next_question
def submit_audit_answer(
    db: Session,
    task_id: str,
    payload: SubmitAuditAnswerRequest,
) -> AuditTaskResponse | None:
    # 确认任务是否存在
    task = db.get(AuditTask, task_id)

    # 不在返回none 路由层返回404
    if task is None:
        return None


    #只有 status 是 questioning 才会继续推进
    if task.status != "questioning":
        return to_audit_task_response(task)


    answer = AuditAnswer(
        task_id=task_id,
        round_no=task.current_round,
        answer=payload.answer,
    )


    db.add(answer)


    next_round = task.current_round + 1

   
    next_question = get_question_by_round(next_round)

    # 表示问题已经问完
    if next_question is None:

        task.status = "answered"

        # 清空下一问题 然后展示问题
        task.next_question = None

    else:
        #更新当前轮次

        task.current_round = next_round

        # What: 保存下一轮问题
        task.next_question = next_question

    db.commit()

    db.refresh(task)

    return to_audit_task_response(task)


    #查询某个体检任务的全部回答
def list_audit_answers_by_task_id(
    db:Session,
    task_id:str,
)->list[AuditAnswer]:
    query = db.query(AuditAnswer)
    query = query.filter(AuditAnswer.task_id==task_id)
    query = query.order_by(AuditAnswer.round_no.asc())


    return query.all()


# What: 获取当前 UTC 时间字符串。
# Why: 分析结果落库时需要记录生成时间。
# How: 使用 ISO 格式，方便排序和展示。
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# What: 保存体检任务风险分析结果。
# Why: /analysis 接口生成的分析不能只返回，还要落库保存。
# How: 创建 AuditAnalysisResult，写入 audit_analysis_results 表。
def create_audit_analysis_result(
    db: Session,
    task_id: str,
    audit_context: str,
    analysis_text: str,
    evidences: list[dict],
    model_name: str | None = None,
    retrieval_method: str = "hybrid",
) -> AuditAnalysisResult:
    # What: 创建分析结果 ORM 对象。
    # Why: SQLAlchemy 需要通过模型对象写入数据库。
    # How: analysis_id 使用 uuid4，created_at_utc 使用当前 UTC 时间。
    result = AuditAnalysisResult(
        analysis_id=str(uuid4()),
        task_id=task_id,
        audit_context=audit_context,
        analysis_text=analysis_text,
        evidences=evidences,
        retrieval_method=retrieval_method,
        model_name=model_name,
        created_at_utc=utc_now_iso(),
    )

    # What: 添加到数据库会话。
    # Why: SQLAlchemy 需要 add 后才能提交。
    # How: db.add(result)。
    db.add(result)

    # What: 提交事务。
    # Why: 让分析结果真正写入 dev.db。
    # How: db.commit()。
    db.commit()

    # What: 刷新对象。
    # Why: 确保返回对象是数据库里的最新状态。
    # How: db.refresh(result)。
    db.refresh(result)

    # What: 返回分析结果对象。
    # Why: 路由层可能需要 analysis_id 和 created_at_utc。
    # How: 返回 result。
    return result


# What: 查询某个任务最近一次分析结果。
# Why: 后面报告接口可以直接拿最近一次分析。
# How: 按 created_at_utc 倒序取第一条。
def get_latest_audit_analysis_result(
    db: Session,
    task_id: str,
) -> AuditAnalysisResult | None:
    return (
        db.query(AuditAnalysisResult)
        .filter(AuditAnalysisResult.task_id == task_id)
        .order_by(AuditAnalysisResult.created_at_utc.desc())
        .first()
    )