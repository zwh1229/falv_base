from app.core.config import Settings,get_settings
import httpx
import re
from typing import Literal

#检查key
def ensure_minimax_chat_ready(settings:Settings)->None:
    if not settings.has_minimax_chat_credentials:
        raise RuntimeError(
            "set chat_key"
        )
#检查embedding key 以及group_id
def ensure_minimax_embedding_ready(settings:Settings)->None:
    if not settings.has_minimax_embedding_credentials:
        raise RuntimeError(
            'set embedding/group_id_key'
        )


#设置请求头
def build_minimax_headers(
    settings:Settings|None=None,
)->dict[str,str]:
    settings = settings or get_settings()

    return {
        "Authorization": f"Bearer {settings.minimax_api_key}",
        "Content-Type": "application/json",
    }


MiniMaxMessage = dict[str,str]
MiniMaxEmbeddingType = Literal["db", "query"]

async def async_minimax_chat_completion(
    messages:list[MiniMaxMessage],
    temperature:float=0.2,
    max_completion_tokens:int=1200,
    settings:Settings|None=None
)->str:
    settings = settings or get_settings()
    ensure_minimax_chat_ready(settings)
    url = f"{settings.minimax_chat_base_url.rstrip('/')}/chat/completions"

    payload = {
    "model": settings.minimax_chat_model,
    "messages": messages,
    "temperature": temperature,
    "max_completion_tokens": max_completion_tokens,
    "thinking": {"type": "disabled"},
}

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers=build_minimax_headers(settings),
            json=payload
        )

    if response.status_code >=400:
        raise RuntimeError(
            f'MiniMax chat request failed:'
            f'status={response.status_code},body={response.text}'
        )
    data = response.json()

    try:
        content = data['choices'][0]['message']['content']
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected MiniMax chat response: {data}") from exc

    return content or ""


async def async_minimax_embed_texts(
    texts:list[str],
    embedding_type:MiniMaxEmbeddingType,
    settings: Settings | None = None,
):
    settings = settings or get_settings()
    ensure_minimax_embedding_ready(settings)

    if not texts:
        return []
    url = (
        f"{settings.minimax_embedding_base_url.rstrip('/')}"
        f"/embeddings?GroupId={settings.minimax_group_id}"
    )

    payload = {
        "texts": texts,
        "model": settings.minimax_embedding_model,
        "type": embedding_type,
    }


    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(
            url,
            headers=build_minimax_headers(settings),
            json=payload,
        )

    if response.status_code >= 400:
        raise RuntimeError(
            f"MiniMax embedding request failed: "
            f"status={response.status_code}, body={response.text}"
        )

    data = response.json()

    vectors = data.get("vectors")
    # 校验类型
    if not isinstance(vectors, list):
        raise RuntimeError(f"Unexpected MiniMax embedding response: {data}")
    # 校验数量
    if len(vectors) != len(texts):
        raise RuntimeError(
            "MiniMax embedding response vector count does not match text count."
        )

    return vectors