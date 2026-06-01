from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db

from app.repositories.audit_task_store import (
    create_audit_task,
    get_audit_task,
    submit_audit_answer,
)

# 导入请求和响应模型
from app.schemas.audit import (
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