from datetime import datetime,timezone
from sqlalchemy.orm import Session
from app.models.legal import LegalRecord
from app.schemas.legal import LegalRecordResponse

#json字段转成 数据库魔宗字段
def build_legal_record_values(record:dict)->dict:
    #id 
    record_id = record['id']
    #国家
    country = record['country']
    #法规领域
    domain = record['domain']
    #路径
    rel_base = f'raw-sources/{country}/{domain}/{record_id}'
    #导入方式
    fetch_method = "local_docx_ingest" if record_id == "CN-DATA-007" else "direct_fetch"
    #http 状态码
    http_status = None if record_id == "CN-DATA-007" else 200


    return {
        "record_id": record_id,
        "country": country,
        "domain": domain,
        "law_title_local": record.get("law_title_local"),
        "law_title_en": record.get("law_title_en"),
        "citation": record.get("citation"),
        "issuing_body": record.get("issuing_body"),
        "effective_date": record.get("effective_date"),
        "is_currently_effective": record.get("is_currently_effective"),
        "valid_until": record.get("valid_until"),
        "official_database": record.get("official_database"),
        "official_url": record.get("official_url"),
        "agent_tags": record.get("agent_tags") or [],
        "retrieval_priority": record.get("retrieval_priority"),
        "fetch_status": "success",
        "fetch_method": fetch_method,
        "http_status": http_status,
        "content_path": f"{rel_base}/content.txt",
        "metadata_path": f"{rel_base}/metadata.json",
        "fetch_status_path": f"{rel_base}/fetch-status.json",
        "content_exists": True,
        "ingested_at_utc": datetime.now(timezone.utc).isoformat(),
    }


    #批量导入/更新法规记录
def upsert_legal_records(
        db:Session,
        records:list[dict],
    )->tuple[int,int]:

    #插入计数器
    inserted_count = 0
    #更新计数器
    updated_count = 0
    #遍历法规

    for record in records:
        #构造数据库字段
        values = build_legal_record_values(record)
        existing = db.get(LegalRecord, values["record_id"])

        if existing is None:
            db.add(LegalRecord(**values))
            inserted_count += 1

        else:
            for key,value in values.items():
                setattr(existing,key,value)
            updated_count += 1

    db.commit()
    return inserted_count, updated_count


def list_legal_records(
    db: Session,
    country: str | None = None,
    domain: str | None = None,
) -> list[LegalRecordResponse]:
    query = db.query(LegalRecord)

    #按国家过滤
    if country:
        query = query.filter(LegalRecord.country == country)

    #按法规领域过滤
    if domain:
        query = query.filter(LegalRecord.domain == domain)

  
    #先按 country，再按 domain，再按 record_id 排序
    records = (
        query.order_by(
            LegalRecord.country.asc(),
            LegalRecord.domain.asc(),
            LegalRecord.record_id.asc(),
        )
        .all()
    )

    #对象转响应模型
    return [LegalRecordResponse.model_validate(record) for record in records]