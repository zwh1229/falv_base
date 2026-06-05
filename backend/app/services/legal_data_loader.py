import json
from pathlib import Path


#法规数据路径
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LEGAL_PACKAGE_PATH = (
    REPO_ROOT
    /"data"
    /"legal"
    /"cn-sg-vn-legal-data-package"
)

#数据文件名
DATASET_FILE_NAME = "cn-sg-vn-legal-dataset.json"

#读取法规数据包主json
def load_legal_dataset(
    package_path:Path |None =None,
)->dict:
    base_path = package_path or DEFAULT_LEGAL_PACKAGE_PATH
    #主json文件路径
    dataset_path = base_path /DATASET_FILE_NAME
    
    if not dataset_path.exists():
        raise FileNotFoundError(f"Legal dataset not found: {dataset_path}")
    
    raw_text = dataset_path.read_text('utf-8')
    dataset = json.loads(raw_text)

    return dataset




def load_legal_records(
    package_path: Path | None = None,
) -> list[dict]:
   
    dataset = load_legal_dataset(package_path)
    records = dataset.get("records", [])

    if not isinstance(records, list):
        raise ValueError("Legal dataset field 'records' must be a list")


    return records
