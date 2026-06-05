from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# What: 引入后端根目录。
# Why: 报告文件需要落到 backend/outputs/reports 之类的固定位置。
# How: 复用配置里已经定义好的 BACKEND_ROOT。
from app.core.config import BACKEND_ROOT

# What: 引入分析结果数据库模型。
# Why: 报告要基于已经落库的风险分析结果生成。
# How: 使用 AuditAnalysisResult 读取 analysis_text、evidences 和 audit_context。
from app.models.audit import AuditAnalysisResult

# What: 引入体检任务响应模型。
# Why: 报告需要任务的企业名称、范围和国家。
# How: 复用 get_audit_task 返回的 AuditTaskResponse。
from app.schemas.audit import AuditTaskResponse


# What: 获取当前 UTC 时间字符串。
# Why: 生成报告时要记录生成时间。
# How: 使用 ISO 格式，便于前端展示和排序。
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# What: 格式化可选文本。
# Why: 企业名称等字段可能为空。
# How: 空值统一显示为“未提供”。
def format_optional_text(value: str | None) -> str:
    if value is None:
        return "未提供"

    cleaned_value = value.strip()

    if not cleaned_value:
        return "未提供"

    return cleaned_value


# What: 格式化国家列表。
# Why: 报告里需要展示适用法域。
# How: 用中文顿号连接多个国家或地区。
def format_countries(countries: list[str]) -> str:
    if not countries:
        return "未提供"

    return "、".join(countries)


# What: 规范化审查范围显示值。
# Why: task.scope 可能是枚举对象，直接拼接会不够友好。
# How: 优先取 value，取不到就退回字符串本身。
def format_scope_value(scope: object) -> str:
    scope_value = getattr(scope, "value", scope)
    return str(scope_value)


# What: 格式化分数。
# Why: 法规依据里要展示检索分，但不需要太多小数。
# How: 尝试转 float 后保留 4 位小数。
def format_score(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "0.0000"


# What: 格式化单条法规依据摘要。
# Why: 报告需要列出本次分析引用了哪些法规。
# How: 从 evidences JSON 里提取法规 ID、标题、chunk 和分数。
def format_evidence_item(evidence: dict, index: int) -> str:
    record_id = evidence.get("record_id", "unknown")
    country = evidence.get("country", "unknown")
    domain = evidence.get("domain", "unknown")
    law_title = evidence.get("law_title", "unknown")
    chunk_index = evidence.get("chunk_index", "unknown")
    hybrid_score = format_score(evidence.get("hybrid_score"))

    return "\n".join(
        [
            f"{index}. **{law_title}**",
            f"   - 法规ID：{record_id}",
            f"   - 国家/地区：{country}",
            f"   - 法规领域：{domain}",
            f"   - Chunk序号：{chunk_index}",
            f"   - Hybrid分数：{hybrid_score}",
        ]
    )


# What: 格式化法规依据列表。
# Why: 报告需要展示法规引用来源。
# How: 遍历 evidences，逐条格式化。
def format_evidence_section(evidences: list[dict]) -> str:
    if not evidences:
        return "未保存法规依据。"

    return "\n\n".join(
        format_evidence_item(evidence, index)
        for index, evidence in enumerate(evidences, start=1)
    )


# What: 构建 Markdown 体检报告。
# Why: 已有风险分析结果后，需要整理成可展示、可导出的报告文本。
# How: 使用任务信息、企业事实、法规依据和分析正文拼接报告。
def build_audit_report_markdown(
    task: AuditTaskResponse,
    analysis_result: AuditAnalysisResult,
    generated_at_utc: str | None = None,
) -> str:
    generated_at = generated_at_utc or utc_now_iso()
    company_name = format_optional_text(task.company_name)
    countries = format_countries(task.countries)
    scope = format_scope_value(task.scope)
    evidence_section = format_evidence_section(analysis_result.evidences)

    return "\n\n".join(
        [
            "# 数据跨境合规体检报告",
            "## 一、报告基本信息",
            "\n".join(
                [
                    f"- 企业名称：{company_name}",
                    f"- 体检任务ID：{task.task_id}",
                    f"- 分析结果ID：{analysis_result.analysis_id}",
                    f"- 审查范围：{scope}",
                    f"- 涉及国家/地区：{countries}",
                    f"- 检索方法：{analysis_result.retrieval_method}",
                    f"- 使用模型：{format_optional_text(analysis_result.model_name)}",
                    f"- 分析生成时间：{analysis_result.created_at_utc}",
                    f"- 报告生成时间：{generated_at}",
                ]
            ),
            "## 二、企业问答事实",
            analysis_result.audit_context,
            "## 三、引用法规依据",
            evidence_section,
            "## 四、合规风险分析",
            analysis_result.analysis_text,
            "## 五、重要说明",
            "本报告由数据跨境合规体检智能体基于企业问答事实和检索到的法规依据自动生成，结果用于合规初筛和内部决策辅助，不替代正式法律意见。",
        ]
    )


# What: 定义报告文件输出目录。
# Why: 下载接口需要把 Markdown 写到一个固定且可预期的位置。
# How: 默认放到 backend/outputs/reports。
REPORT_OUTPUT_DIR = BACKEND_ROOT / "outputs" / "reports"

PDF_FONT_NAME = "ComplianceCJK"
PDF_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
    Path("C:/Windows/Fonts/simsun.ttc"),
]


# What: 生成报告文件名。
# Why: 不同任务和不同分析结果需要有唯一文件名。
# How: 用 task_id 和 analysis_id 拼接出可读文件名。
def build_report_file_name(task_id: str, analysis_id: str) -> str:
    return f"audit_report_{task_id}_{analysis_id}.md"


# What: 生成 PDF 报告文件名。
# Why: 前端下载报告时需要真实 PDF 文件。
# How: 沿用 task_id 和 analysis_id，扩展名改为 .pdf。
def build_report_pdf_file_name(task_id: str, analysis_id: str) -> str:
    return f"audit_report_{task_id}_{analysis_id}.pdf"


# What: 获取 PDF 报告目标路径。
# Why: 下载接口可以先检查文件是否已经存在，避免重复生成 PDF。
# How: 使用固定输出目录和固定文件名拼接路径。
def get_audit_report_pdf_path(
    task_id: str,
    analysis_id: str,
    output_dir: Path | None = None,
) -> Path:
    target_dir = output_dir or REPORT_OUTPUT_DIR
    return target_dir / build_report_pdf_file_name(task_id, analysis_id)


# What: 保存 Markdown 报告文件。
# Why: 前端下载或人工留档时，需要真实的 .md 文件。
# How: 先创建目录，再写入 UTF-8 文本并返回路径。
def save_audit_report_markdown_file(
    task_id: str,
    analysis_id: str,
    report_text: str,
    output_dir: Path | None = None,
) -> Path:
    target_dir = output_dir or REPORT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    report_path = target_dir / build_report_file_name(task_id, analysis_id)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


# What: 注册 PDF 中文字体。
# Why: ReportLab 默认字体不支持中文，直接生成会乱码。
# How: 优先使用 Windows 自带 SimHei，找不到再尝试其他中文字体。
def register_pdf_font() -> str:
    for font_path in PDF_FONT_CANDIDATES:
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(font_path)))
                return PDF_FONT_NAME
            except Exception:
                continue

    return "Helvetica"


# What: 构建 PDF 样式。
# Why: PDF 需要比纯文本更容易扫读，标题、正文、列表要有层级。
# How: 使用同一个中文字体定义标题、二级标题、正文和列表样式。
def build_pdf_styles(font_name: str) -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            name="ComplianceTitle",
            fontName=font_name,
            fontSize=20,
            leading=28,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17222d"),
            spaceAfter=14,
        ),
        "heading": ParagraphStyle(
            name="ComplianceHeading",
            fontName=font_name,
            fontSize=14,
            leading=22,
            textColor=colors.HexColor("#153e4d"),
            spaceBefore=12,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            name="ComplianceBody",
            fontName=font_name,
            fontSize=10.5,
            leading=17,
            textColor=colors.HexColor("#263844"),
            spaceAfter=6,
        ),
        "list": ParagraphStyle(
            name="ComplianceList",
            fontName=font_name,
            fontSize=10.5,
            leading=17,
            leftIndent=12,
            firstLineIndent=0,
            textColor=colors.HexColor("#263844"),
            spaceAfter=5,
        ),
    }


# What: 清理 Markdown 行内标记。
# Why: ReportLab Paragraph 不需要 Markdown 原始符号。
# How: 去掉加粗、代码等标记，并转义 XML 特殊字符。
def clean_markdown_inline(text: str) -> str:
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    return escape(cleaned)


# What: 把 Markdown 文本转换成 PDF 元素。
# Why: 报告正文仍然由 Markdown 生成，但 PDF 需要 Platypus flowables。
# How: 按行识别标题、二级标题、列表和普通段落。
def build_pdf_story(report_text: str, styles: dict[str, ParagraphStyle]) -> list:
    story: list = []

    for raw_line in report_text.splitlines():
        line = raw_line.strip()

        if not line:
            story.append(Spacer(1, 4))
            continue

        if line.startswith("# "):
            story.append(Paragraph(clean_markdown_inline(line[2:].strip()), styles["title"]))
            continue

        if line.startswith("## "):
            story.append(Paragraph(clean_markdown_inline(line[3:].strip()), styles["heading"]))
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)$", line)
        if bullet_match:
            story.append(
                Paragraph(
                    clean_markdown_inline(bullet_match.group(1)),
                    styles["list"],
                    bulletText="-",
                )
            )
            continue

        story.append(Paragraph(clean_markdown_inline(line), styles["body"]))

    return story


# What: 绘制 PDF 页脚。
# Why: 多页报告需要页码，方便人工审阅。
# How: 在每页底部写入当前页码。
def draw_pdf_footer(canvas, doc, font_name: str) -> None:
    canvas.saveState()
    canvas.setFont(font_name, 8)
    canvas.setFillColor(colors.HexColor("#687781"))
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


# What: 保存 PDF 报告文件。
# Why: 用户最终更需要可下载、可流转的 PDF 报告。
# How: 将 Markdown 报告转换为 PDF，并返回生成路径。
def save_audit_report_pdf_file(
    task_id: str,
    analysis_id: str,
    report_text: str,
    output_dir: Path | None = None,
) -> Path:
    target_dir = output_dir or REPORT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    report_path = get_audit_report_pdf_path(task_id, analysis_id, target_dir)
    font_name = register_pdf_font()
    styles = build_pdf_styles(font_name)
    story = build_pdf_story(report_text, styles)

    doc = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="数据跨境合规体检报告",
    )
    doc.build(
        story,
        onFirstPage=lambda canvas, document: draw_pdf_footer(canvas, document, font_name),
        onLaterPages=lambda canvas, document: draw_pdf_footer(canvas, document, font_name),
    )

    return report_path
