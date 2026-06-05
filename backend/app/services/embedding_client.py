from app.core.config import Settings, get_settings
import httpx

def ensure_ada_embedding_ready(settings: Settings) -> None:
    if not settings.has_ada_embedding_credentials:
        raise RuntimeError(
            "ada-002 embedding credentials are not configured. "
            "Please set AZURE_API_KEY_textada002 and AZURE_ENDPOINT_textada002 in backend/.env."
        )



def build_ada_embedding_headers(
    settings: Settings | None = None,
) -> dict[str, str]:


    settings = settings or get_settings()


    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.azure_api_key_textada002}",
    }




async def async_embed_texts(
    texts: list[str],
    settings: Settings | None = None,
) -> list[list[float]]:

    settings = settings or get_settings()

    ensure_ada_embedding_ready(settings)

    if not texts:
        return []

    payload = {
        "model": settings.embedding_model,
        "input": texts,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.azure_endpoint_textada002,
            headers=build_ada_embedding_headers(settings),
            json=payload,
        )

    response.raise_for_status()

    data = response.json()

    items = data["data"]

    return [item["embedding"] for item in items]