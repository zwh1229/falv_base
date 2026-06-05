# What: 引入异步运行工具。
# Why: httpx 异步请求需要 asyncio.run 启动。
# How: 使用 Python 标准库 asyncio。
import asyncio

# What: 引入环境变量读取工具。
# Why: API key 和 endpoint 不能写死在代码里。
# How: 使用 os.getenv 从 .env 读取。
import os

# What: 引入 HTTP 客户端。
# Why: 需要请求 56 的 chat/completions 接口。
# How: 使用 httpx.AsyncClient 发 POST 请求。
import httpx

# What: 引入 dotenv 加载工具。
# Why: 本地 .env 里的配置需要加载进环境变量。
# How: load_dotenv 会自动读取 backend/.env。
from dotenv import load_dotenv


# What: 加载 .env 文件。
# Why: 让 AZURE_API_KEY、AZURE_ENDPOINT、CHAT_MODEL 生效。
# How: 调用 load_dotenv。
load_dotenv()


# What: 读取 56 Chat API key。
# Why: 请求 chat 接口需要鉴权。
# How: 从 .env 的 AZURE_API_KEY 读取。
CHAT_API_KEY = os.getenv("AZURE_API_KEY")

# What: 读取 56 Chat endpoint。
# Why: 请求要发到 192.168.1.56 的中转地址。
# How: 从 .env 的 AZURE_ENDPOINT 读取。
CHAT_ENDPOINT = os.getenv("AZURE_ENDPOINT")

# What: 读取 Chat 模型名。
# Why: 中转接口需要知道调用哪个模型。
# How: 默认使用 gpt-4o-mini。
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")


# What: 检查配置是否完整。
# Why: 没配置时直接报清楚，避免请求时报奇怪错误。
# How: key 或 endpoint 为空就抛 RuntimeError。
def ensure_chat_config_ready() -> None:
    if not CHAT_API_KEY or not CHAT_ENDPOINT:
        raise RuntimeError("Please set AZURE_API_KEY and AZURE_ENDPOINT in backend/.env")


# What: 执行一次 56 Chat 测试。
# Why: 确认本地中转能正常生成回答。
# How: 发 OpenAI-compatible /v1/chat/completions 请求。
async def main() -> None:
    ensure_chat_config_ready()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHAT_API_KEY}",
    }

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个简洁、严谨的中文法律合规助手。",
            },
            {
                "role": "user",
                "content": "请用一句话说明数据出境安全评估和个人信息出境标准合同的区别。",
            },
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            CHAT_ENDPOINT,
            headers=headers,
            json=payload,
        )

    print("status_code =", response.status_code)

    response.raise_for_status()

    data = response.json()

    content = data["choices"][0]["message"]["content"]

    print("model =", CHAT_MODEL)
    print("answer =", content)


# What: 脚本入口。
# Why: 直接 python scripts/test_chat_56.py 时要执行 main。
# How: asyncio.run 启动异步函数。
if __name__ == "__main__":
    asyncio.run(main())