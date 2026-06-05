# What: 引入配置类型和读取函数。
# Why: Chat key、endpoint、model 都要从 .env 读取。
# How: 使用 get_settings 获取 Settings。
from app.core.config import Settings, get_settings

# What: 引入 HTTP 客户端。
# Why: 56 Chat 中转是 HTTP API。
# How: 使用 httpx.AsyncClient 发异步 POST 请求。
import httpx


# What: 定义 Chat message 类型。
# Why: OpenAI-compatible Chat 接口使用 role/content 格式。
# How: role 和 content 都是字符串。
ChatMessage = dict[str, str]


# What: 检查 56 Chat 配置是否完整。
# Why: key 或 endpoint 缺失时应该提前报清楚。
# How: 使用 Settings.has_azure_chat_credentials。
def ensure_azure_chat_ready(settings: Settings) -> None:
    if not settings.has_azure_chat_credentials:
        raise RuntimeError(
            "56 chat credentials are not configured. "
            "Please set AZURE_API_KEY and AZURE_ENDPOINT in backend/.env."
        )


# What: 构建 56 Chat 请求头。
# Why: OpenAI-compatible 接口需要 Bearer token。
# How: Authorization 使用 .env 里的 AZURE_API_KEY。
def build_azure_chat_headers(
    settings: Settings | None = None,
) -> dict[str, str]:
    settings = settings or get_settings()

    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.azure_api_key}",
    }


# What: 调用 56 Chat completion。
# Why: 风险分析需要调用 OpenAI-compatible Chat 模型。
# How: POST 到 AZURE_ENDPOINT，解析 choices[0].message.content。
async def async_azure_chat_completion(
    messages: list[ChatMessage],
    temperature: float = 0.2,
    max_tokens: int = 1800,
    settings: Settings | None = None,
) -> str:
    settings = settings or get_settings()

    ensure_azure_chat_ready(settings)

    payload = {
        "model": settings.chat_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            settings.azure_endpoint,
            headers=build_azure_chat_headers(settings),
            json=payload,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            "56 chat request failed: "
            f"status={response.status_code}, body={response.text}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected 56 chat response: {data}") from exc

    return content or ""