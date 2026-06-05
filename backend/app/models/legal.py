from sqlalchemy import Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


# 定义一个法规主记录模型
class LegalRecord(Base):
    __tablename__ = "legal_records"

    # id
    record_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)

    # 国家或地区
    country: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # 法规领域
    domain: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    # 法规本地语言标题
    law_title_local: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 法规英文标题
    law_title_en: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 引用信息
    citation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 发布机关
    issuing_body: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 检查是否有效
    is_currently_effective: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # 生效日期
    effective_date: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # 失效日期
    valid_until: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # 官方数据库名称
    official_database: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 官方url
    official_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 智能体标签
    agent_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    # 检索优先级
    retrieval_priority: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # 抓取状态
    fetch_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 抓取或导入方式
    fetch_method: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # http 状态码
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 正文文件路径
    content_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 元数据文件路径
    metadata_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 抓取状态文件路径
    fetch_status_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 正文是否存在
    content_exists: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 入库时间
    ingested_at_utc: Mapped[str | None] = mapped_column(String(50), nullable=True)
