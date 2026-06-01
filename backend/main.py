from fastapi import FastAPI
from app.api.routes.health import router as health_router
from app.api.routes.audit_tasks import router as audit_tasks_router
from app.models.audit import AuditAnswer, AuditTask
from app.db.session import Base, engine


Base.metadata.create_all(bind=engine)





app = FastAPI(
    title="数据跨境合规审核法律智能体",
    version="0.1.0",
)

# 健康查询
app.include_router(
    health_router,
    prefix="/api/v1",
)
# 体检接口
app.include_router(
    audit_tasks_router,
    prefix="/api/v1",
)


