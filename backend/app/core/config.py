# What: 引入缓存工具。
# Why: 配置对象只需要创建一次，不需要每次都重新读取 .env。
# How: lru_cache 会缓存 get_settings 的返回值。
from functools import lru_cache

# What: 引入路径工具。
# Why: 我们需要稳定定位 backend/.env。
# How: Path 可以跨平台处理路径。
from pathlib import Path

# What: 引入 Pydantic Settings。
# Why: 后端配置要从 .env 和环境变量读取。
# How: BaseSettings 读取配置，SettingsConfigDict 指定 .env 路径。
from pydantic_settings import BaseSettings, SettingsConfigDict


# What: 定位 backend 目录。
# Why: .env 会放在 backend/.env。
# How: config.py 位于 backend/app/core，所以 parents[2] 是 backend。
BACKEND_ROOT = Path(__file__).resolve().parents[2]


# What: 定义后端统一配置类。
# Why: MiniMax key、模型名、base_url 不应该散落在业务代码里。
# How: 后面所有模块都通过 get_settings() 读取配置。
class Settings(BaseSettings):
    # What: MiniMax API key。
    # Why: Chat 和 Embedding 调用都需要它鉴权。
    # How: 从 MINIMAX_API_KEY 环境变量读取，代码里不写真实值。
    minimax_api_key: str = ""

    # What: MiniMax Chat 模型名。
    # Why: 后面风险分析和报告生成要用 Chat 模型。
    # How: 先使用官方当前更稳的 MiniMax-M2.7。
    minimax_chat_model: str = "MiniMax-M2.7"

    # What: MiniMax Chat 接口基础地址。
    # Why: Chat 走 OpenAI-compatible 接口，不需要 group_id。
    # How: 后面 client 会拼接 /chat/completions。
    minimax_chat_base_url: str = "https://api.minimaxi.com/v1"

    # What: MiniMax Group ID。
    # Why: Embedding 的 embo-01 接口需要 GroupId。
    # How: 只在 embedding 调用时使用，chat 不用它。
    minimax_group_id: str = ""

    # What: MiniMax Embedding 模型名。
    # Why: 法规正文和用户问答上下文要转成向量。
    # How: 使用 MiniMax 的 embo-01。
    minimax_embedding_model: str = "embo-01"

    # What: MiniMax Embedding 接口基础地址。
    # Why: Embedding 接口和 Chat 接口地址不同。
    # How: 后面 client 会拼接 /embeddings?GroupId=xxx。
    minimax_embedding_base_url: str = "https://api.minimax.chat/v1"



    azure_api_key_textada002: str = ""

    azure_endpoint_textada002: str = ""

    embedding_model: str = "text-embedding-ada-002"


        # What: 56 Chat 中转 API key。
    # Why: MiniMax 限额时，风险分析可以改走 56 的 OpenAI-compatible Chat。
    # How: 从 .env 的 AZURE_API_KEY 读取，不在代码里写真实 key。
    azure_api_key: str = ""

    # What: 56 Chat 中转 endpoint。
    # Why: 风险分析需要请求 /v1/chat/completions。
    # How: 从 .env 的 AZURE_ENDPOINT 读取。
    azure_endpoint: str = ""

    # What: Chat 模型名称。
    # Why: 56 中转需要知道调用哪个模型。
    # How: 当前用 gpt-4o-mini，后面有 4o 权限后只改 .env。
    chat_model: str = "gpt-4o-mini"





    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def has_ada_embedding_credentials(self) -> bool:
        return bool(
            self.azure_api_key_textada002
            and self.azure_endpoint_textada002
        )
    @property
    def has_minimax_chat_credentials(self) -> bool:
        return bool(self.minimax_api_key)


    @property
    def has_minimax_embedding_credentials(self) -> bool:
        return bool(self.minimax_api_key and self.minimax_group_id)


        
    @property
    def has_azure_chat_credentials(self) -> bool:
        return bool(
            self.azure_api_key
            and self.azure_endpoint
        )

#全局配置对象。
@lru_cache
def get_settings() -> Settings:
    return Settings()