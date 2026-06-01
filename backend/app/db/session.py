# What: 从 typing 导入 Generator
# Why: get_db 会用 yield 返回数据库连接，需要标注它是一个生成器
# How: Generator[Session, None, None] 表示它产出 Session，不接收值，不返回最终值
from collections.abc import Generator

# What: 导入 SQLAlchemy 的 create_engine
# Why: 后端需要创建一个数据库引擎来连接 SQLite
# How: create_engine(DATABASE_URL) 会根据数据库地址创建连接入口
from sqlalchemy import create_engine

# What: 导入 SQLAlchemy 的 DeclarativeBase
# Why: 所有数据库表模型都要继承一个统一的 Base
# How: 后面 AuditTask、AuditAnswer 会继承 Base，SQLAlchemy 才知道它们是表
from sqlalchemy.orm import DeclarativeBase

# What: 导入 SQLAlchemy 的 Session 和 sessionmaker
# Why: 后端每次操作数据库都需要一个 Session
# How: sessionmaker 会帮我们批量创建数据库会话
from sqlalchemy.orm import Session, sessionmaker


# What: 本地 SQLite 数据库地址
# Why: 现在先不用真实 PolarDB，本地生成 dev.db 文件模拟数据库
# How: sqlite:///./dev.db 表示在 backend 当前目录下创建 dev.db
DATABASE_URL = "sqlite:///./dev.db"


# What: 创建数据库引擎
# Why: SQLAlchemy 需要 engine 才能真正连接数据库
# How: connect_args={"check_same_thread": False} 是 SQLite 在 FastAPI 下常用配置
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


# What: 创建数据库会话工厂
# Why: 每个请求都应该拿一个独立的数据库 Session
# How: SessionLocal() 每调用一次，就创建一个新的数据库会话
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# What: 定义所有 ORM 模型的基类
# Why: 后面所有数据库表都要继承它
# How: SQLAlchemy 会从 Base.metadata 里收集所有表结构
class Base(DeclarativeBase):
    pass


# What: 给 FastAPI 使用的数据库依赖函数
# Why: API 接口需要通过 Depends(get_db) 拿到数据库连接
# How: yield db 把连接交给接口，用完后 finally 自动关闭
def get_db() -> Generator[Session, None, None]:
    # What: 创建一个新的数据库会话
    # Why: 当前请求需要用它查询或写入数据库
    # How: SessionLocal() 会基于上面的 engine 创建 Session
    db = SessionLocal()

    try:
        # What: 把数据库会话交给调用方
        # Why: 路由函数和仓储函数需要用这个 db 操作数据库
        # How: yield 会暂停在这里，等请求处理完成后继续执行 finally
        yield db

    finally:
        # What: 关闭数据库会话
        # Why: 防止连接泄漏
        # How: 请求结束后自动执行 db.close()
        db.close()