from sqlalchemy import Boolean,JSON,String,Text
from sqlalchemy.orm  import Mapped,mapped_column
from app.db.session import Base

#定义一个法规 主记录模型
class LegaLRecord(Base):
    __tablename__='legal_records'
    #id 
    record_id:Mapped[str] = mapped_column(String(50),primary_key=True,index=True)
    #国家或地区
    country:Mapped[str] = mapped_column(String(50),nullable=False,index=True)
    #法规领域
    domain:Mapped[str] = mapped_column(String(80),nullable=False, index=True)
    #法规本地语言标题
    law_title_local:Mapped[str | None] = mapped_column(Text,nullable=True)
    #法规英文标题
    law_title_en:Mapped[str| None] = mapped_column(Text,nullable=True)
    #引用信息
    citation:Mapped[str|None] = mapped_column(Text,nullable=True)
    #发布机关
    issuing_body:Mapped[str|None] = mapped_column(Text,nullable=True)
    #生效日期
    effective_date:Mapped[str|None] = mapped_column(Boolean,nullable=True)
    #失效日期
    valid_until: Mapped[str | None] = mapped_column(String(30), nullable=True)
    #官方数据库名称
    official_database:Mapped[str|None] =mapped_column(Text,nullable=True)
    #官方url
    official_url :Mapped[str|None] = mapped_column(Text,nullable=True)
    #智能体标签
    agent_tags:Mapped[str|None] = mapped_column(JSON,nullable=False,default=list)
    #检索优先级
    retrieval_priority:Mapped[str|None] = mapped_column(String(30),nullable=True)