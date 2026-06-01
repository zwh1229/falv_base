from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.audit import AuditAnswer, AuditTask


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
        # What: 更新当前轮次
        # Why: 系统进入下一轮问答
        # How: current_round 改成 next_round
        task.current_round = next_round

        # What: 保存下一轮问题
        # Why: 前端提交回答后，需要立刻显示新问题
        # How: next_question 来自 get_question_by_round
        task.next_question = next_question

    # What: 提交数据库事务
    # Why: 回答记录和任务状态更新需要一起保存
    # How: db.commit() 会把 answer 和 task 的变化写入 SQLite
    db.commit()

    # What: 刷新任务对象
    # Why: 确保拿到数据库里的最新任务状态
    # How: db.refresh(task) 会重新读取任务记录
    db.refresh(task)

    # What: 返回更新后的任务
    # Why: 前端需要知道下一轮问题或问答已结束
    # How: 转成 AuditTaskResponse 返回
    return to_audit_task_response(task)