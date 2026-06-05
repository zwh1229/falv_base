from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.legal import LegalImportResponse,LegalRecordResponse
from app.services.legal_data_loader import load_legal_dataset
from app.repositories.legal_store import upsert_legal_records,list_legal_records

#法规数据路由对象
router = APIRouter(prefix="/legal-data", tags=["legal-data"])




#导入法规数据接口
@router.post('/import',response_model=LegalImportResponse)
def import_legal_data(
    db:Session=Depends(get_db)
)->LegalImportResponse:

    try:
        dataset = load_legal_dataset()
    except FileNotFoundError  as exc:
        raise HTTPException(status_code=500,detail=str(exc)) from exc

    records = dataset.get("records", [])
    if not isinstance(records,list):
        raise HTTPException(
            status_code=500,
            detail="must be a list"
        )

    inserted_count, updated_count = upsert_legal_records(db, records)

    return LegalImportResponse(
        package_name=dataset.get("package_name", "unknown"),
        validity_as_of=dataset.get("validity_as_of"),
        total_records=len(records),
        inserted_records=inserted_count,
        updated_records=updated_count,
    )


# 查询入库的法规主记录
@router.get('/records',response_model=list[LegalRecordResponse])
def get_legal_records(
    country:str|None=None,
    domain:str|None = None,
    db:Session = Depends(get_db)
)->list[LegalRecordResponse]:

    return list_legal_records(
        db=db,
        country=country,
        domain=domain,
    )