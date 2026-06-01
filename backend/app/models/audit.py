# What: 导入 ForeignKey、Integer、JSON、String、Text 这些数据库字段工具
# Why: 定义表字段时需要指定字段类型，比如字符串、整数、长文本、JSON
# How: SQLAlchemy 会把这些类型转换成 SQLite 能识别的字段类型
from sqlalchemy import ForeignKey, Integer, JSON, String, Text

# What: 导入 Mapped 和 mapped_column
# Why: SQLAlchemy 2.x 推荐用这种方式定义 ORM 字段
# How: Mapped 标注 Python 类型，mapped_column 配置数据库字段
from sqlalchemy.orm import Mapped, mapped_column

# What: 导入我们刚才定义的 Base
# Why: 所有表模型都必须继承 Base
# How: 继承 Base 后，SQLAlchemy 才能把这个类识别成数据库表
from app.db.session import Base


# What: 定义体检任务表模型
# Why: 每个企业发起一次体检，都要保存成一条任务记录
# How: 这个类会映射到数据库里的 audit_tasks 表
class AuditTask(Base):
    # What: 指定数据库表名
    # Why: SQLAlchemy 需要知道这个模型对应哪张表
    # How: __tablename__ 的值就是真实表名
    __tablename__ = "audit_tasks"

    # What: 任务 ID 字段
    # Why: 每个任务都需要唯一标识，后续查询、提交回答都靠它
    # How: String(36) 用来保存 UUID 字符串，primary_key=True 表示主键
    task_id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)

    # What: 企业名称字段
    # Why: 报告和任务列表里需要显示企业名称
    # How: nullable=True 表示可以为空，MVP 阶段允许用户暂时不填
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # What: 审查范围字段
    # Why: 要记录用户选的是中国、中国+越南，还是中国+新加坡
    # How: 这里先存字符串，比如 china_singapore
    scope: Mapped[str] = mapped_column(String(50), nullable=False)

    # What: 国家列表字段
    # Why: 后续检索法律知识库时，要知道需要查哪些国家
    # How: JSON 字段可以保存 ["China", "Singapore"] 这种列表
    countries: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    # What: 任务状态字段
    # Why: 任务会经历 questioning、answered、analyzing、completed 等状态
    # How: 这里先用字符串保存状态
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    # What: 当前问答轮次
    # Why: 系统需要知道现在问到第几轮
    # How: Integer 保存轮次数字，默认从 1 开始
    current_round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # What: 下一轮问题
    # Why: 前端需要直接展示当前要问用户的问题
    # How: Text 可以保存较长的问题文本，nullable=True 表示问答结束时可以为空
    next_question: Mapped[str | None] = mapped_column(Text, nullable=True)


# What: 定义用户回答表模型
# Why: 每一轮问答都要保存用户回答，后面生成报告要用
# How: 这个类会映射到数据库里的 audit_answers 表
class AuditAnswer(Base):
    # What: 指定数据库表名
    # Why: SQLAlchemy 需要知道这个模型对应哪张表
    # How: __tablename__ 的值就是真实表名
    __tablename__ = "audit_answers"

    # What: 回答记录 ID
    # Why: 每条回答也需要自己的唯一编号
    # How: Integer 主键自增，SQLite 会自动生成
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # What: 所属任务 ID
    # Why: 每条回答都必须知道属于哪个体检任务
    # How: ForeignKey("audit_tasks.task_id") 表示关联 audit_tasks 表的 task_id
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("audit_tasks.task_id"),
        index=True,
        nullable=False,
    )

    # What: 回答对应的轮次
    # Why: 需要知道这是第 1 轮、第 2 轮还是第 5 轮的回答
    # How: Integer 保存轮次数字
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)

    # What: 用户回答正文
    # Why: 后续槽位抽取、风险判断、报告生成都要基于这些回答
    # How: Text 可以保存较长的自然语言回答
    answer: Mapped[str] = mapped_column(Text, nullable=False)
