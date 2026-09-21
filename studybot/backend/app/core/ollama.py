"""Minimal Ollama client. Grows in Phase 1 with chat and embedding calls."""
import httpx


async def list_models(base_url: str, timeout: float = 2.0) -> list[str]:
    """Return the names of models pulled into the local Ollama, e.g. ['llama3.2:3b']."""
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        response = await client.get("/api/tags")
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]


def normalize_model_name(name: str) -> str:
    """Ollama treats a bare 'llama3.2' as 'llama3.2:latest'."""
    return name if ":" in name else f"{name}:latest"
