from fastapi import FastAPI

from app.api.routes.audit_tasks import router as audit_tasks_router
from app.api.routes.health import router as health_router
from app.db.session import Base, engine
from app.models.audit import AuditAnswer, AuditTask
from app.models.legal import LegalRecord
from app.api.routes.legal_data import router as legal_data_router
from app.api.routes.legal_search import router as legal_search_router





Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="数据跨境合规体检智能体",
    version="0.1.0",
)


# 健康检查
app.include_router(
    health_router,
    prefix="/api/v1",
)


# 体检任务接口
app.include_router(
    audit_tasks_router,
    prefix="/api/v1",
)
#挂载法规数据接口
app.include_router(
    legal_data_router,
    prefix='/api/v1'
)
# 搜索路由
app.include_router(
    legal_search_router,
    prefix="/api/v1",
)