from pydantic import BaseModel, ConfigDict


# 定义法规记录响应模型
class LegalRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # 法规记录 ID
    record_id: str
    # 国家或地区
    country: str
    # 法规领域
    domain: str
    # 法规本地语言标题
    law_title_local: str | None = None
    # 法规英文标题
    law_title_en: str | None = None
    # 引用信息
    citation: str | None = None
    # 发布机关
    issuing_body: str | None = None
    # 当前是否有效
    is_currently_effective: bool | None = None
    # 生效日期
    effective_date: str | None = None
    # 失效日期
    valid_until: str | None = None
    # 官方数据库名称
    official_database: str | None = None
    # 官方 URL
    official_url: str | None = None
    # 智能体标签
    agent_tags: list[str]
    # 检索优先级
    retrieval_priority: str | None = None
    # 抓取状态
    fetch_status: str | None = None
    # 抓取或导入方式
    fetch_method: str | None = None
    # HTTP 状态码
    http_status: int | None = None
    # 正文文件路径
    content_path: str | None = None
    # 元数据文件路径
    metadata_path: str | None = None
    # 抓取状态文件路径
    fetch_status_path: str | None = None
    # 正文是否存在
    content_exists: bool = False
    # 入库时间
    ingested_at_utc: str | None = None


# 定义法规数据导入响应模型
class LegalImportResponse(BaseModel):
    # 数据包名称
    package_name: str

    # 数据包有效日期
    validity_as_of: str | None = None

    # 数据包总记录数
    total_records: int

    # 本次新插入记录数
    inserted_records: int

    # 本次更新记录数
    updated_records: int
