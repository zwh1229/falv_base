# What: 引入法规依据格式化函数。
# Why: 风险分析 prompt 需要把 Hybrid 命中结果整理成法规依据区块。
# How: 使用 format_legal_evidence_block。
from app.services.legal_evidence_formatter import format_legal_evidence_block

# What: 引入 Hybrid 命中结构。
# Why: build_risk_analysis_prompt 接收 LegalHybridHit 列表。
# How: 从 legal_hybrid_retriever.py 导入。
from app.services.legal_hybrid_retriever import LegalHybridHit
# What: 引入 56 Chat 异步调用函数。
# Why: MiniMax 当前额度受限，风险分析先走 56 的 OpenAI-compatible Chat。
# How: 使用 azure_chat_client.py 里封装好的 async_azure_chat_completion。
from app.services.azure_chat_client import async_azure_chat_completion

# What: 定义风险分析系统提示词。
# Why: 需要约束大模型扮演数据跨境合规审核法律智能体。
# How: 用固定中文 system prompt 规定角色、边界和输出要求。
RISK_ANALYSIS_SYSTEM_PROMPT = """
你是数据跨境合规审核法律智能体，任务是基于企业事实和给定法规依据，识别数据跨境合规风险。

你必须遵守以下规则：
1. 只能基于用户提供的企业事实和法规依据进行分析。
2. 不得编造法规名称、条款、义务或结论。
3. 如果法规依据不足，必须明确说明“现有法规依据不足以判断”。
4. 风险判断要区分：高风险、中风险、低风险、待补充信息。
5. 输出必须结构化，便于后端后续生成报告。
6. 如果不同法规依据存在新旧口径差异，应优先适用更新、更特别的规则。
7. 对中国数据出境场景，《促进和规范数据跨境流动规定》的新口径应优先于较早办法中的旧阈值口径。
8. 非关键信息基础设施运营者向境外提供10万人以上、不满100万人个人信息且不含敏感个人信息时，不要直接判断为必须申报数据出境安全评估；应重点判断标准合同、认证、个人信息保护影响评估、备案等义务。
""".strip()


# What: 定义风险分析输出格式要求。
# Why: 后续报告生成需要稳定结构。
# How: 用 prompt 明确要求模型按固定栏目输出。
RISK_ANALYSIS_OUTPUT_INSTRUCTIONS = """
请按以下结构输出：

一、结论总览
- 综合等级：高风险/中风险/低风险/待补充信息
- 结论一句话：用一句普通业务人员能听懂的话说明当前最需要处理什么。
- 重点风险数量：数字
- 一般风险数量：数字
- 待补充信息数量：数字
- 用户优先动作：用一句话说明用户今天应该先做什么。

二、企业事实摘要
- 已知事实：
- 缺失信息：

三、适用法规依据
- 请引用法规ID和法规标题说明依据。

四、主要合规风险
- 重点风险1：风险标题；为什么有风险；应立即做什么；依据的法规ID和标题。
- 重点风险2：风险标题；为什么有风险；应立即做什么；依据的法规ID和标题。
- 一般风险1：风险标题；为什么有风险；建议动作；依据的法规ID和标题。

五、建议补充材料
- 材料1：
- 材料2：
- 材料3：

六、后续合规动作建议
- 动作1：
- 动作2：
- 动作3：
""".strip()


# What: 构建风险分析用户提示词。
# Why: MiniMax-M3 需要同时看到企业事实、法规依据和输出要求。
# How: 把 audit_context、legal_evidence_block 和输出格式拼成一个 prompt。
def build_risk_analysis_user_prompt(
    audit_context: str,
    legal_hits: list[LegalHybridHit],
) -> str:
    # What: 格式化法规依据。
    # Why: 大模型需要清楚看到命中的法规来源和正文片段。
    # How: 使用 format_legal_evidence_block。
    legal_evidence_block = format_legal_evidence_block(legal_hits)

    # What: 处理空企业上下文。
    # Why: 没有问答事实时，大模型必须知道信息不足。
    # How: 空字符串时写成固定提示。
    normalized_audit_context = audit_context.strip() or "未提供企业问答事实。"

    # What: 拼接完整用户 prompt。
    # Why: 用户 prompt 是风险分析的主要输入。
    # How: 分成企业事实、法规依据、输出要求三块。
    return "\n\n".join(
        [
            "【企业问答事实】",
            normalized_audit_context,
            legal_evidence_block,
            "【输出要求】",
            RISK_ANALYSIS_OUTPUT_INSTRUCTIONS,
        ]
    )




# What: 调用大模型生成风险分析。
# Why: Hybrid 检索只负责找到法规依据，真正的合规判断需要结合企业事实和法规依据进行分析。
# How: 构建 system prompt 和 user prompt，然后调用 async_minimax_chat_completion。
async def analyze_cross_border_risk(
    audit_context: str,
    legal_hits: list[LegalHybridHit],
) -> str:
    # What: 构建风险分析 user prompt。
    # Why: user prompt 里包含企业问答事实、法规依据和输出格式要求。
    # How: 使用 build_risk_analysis_user_prompt。
    user_prompt = build_risk_analysis_user_prompt(
        audit_context=audit_context,
        legal_hits=legal_hits,
    )

    # What: 组装 Chat messages。
    # Why: MiniMax Chat 接口使用 OpenAI-compatible messages 格式。
    # How: system 负责角色约束，user 负责本次任务输入。
    messages = [
        {
            "role": "system",
            "content": RISK_ANALYSIS_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]


    result = await async_azure_chat_completion(
    messages=messages,
    temperature=0.2,
    max_tokens=1800,
)

    # What: 返回清理后的模型输出。
    # Why: 上层接口和报告生成需要直接使用干净文本。
    # How: strip 去掉首尾空白。
    return result.strip()
