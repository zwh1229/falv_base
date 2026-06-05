from pathlib import Path
from app.services.legal_data_loader import DEFAULT_LEGAL_PACKAGE_PATH






# 读取法规正文内容
def read_legal_content(content_path: str | None) -> str:
    if not content_path:
        return ""

    full_path: Path = DEFAULT_LEGAL_PACKAGE_PATH / content_path
    if not full_path.exists():
        return ""

    #读取正文文本。
    return full_path.read_text(encoding="utf-8")