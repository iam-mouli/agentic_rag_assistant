from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config.settings import settings

# Lazily initialised — created on first call, reused thereafter
_generation_model: BaseChatModel | None = None
_grader_model: BaseChatModel | None = None
_embedder = None


# ---------------------------------------------------------------------------
# Internal factories
# ---------------------------------------------------------------------------

def _make_chat_model(model_name: str) -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=settings.OPENAI_API_KEY)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=settings.ANTHROPIC_API_KEY)
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=settings.GOOGLE_API_KEY)
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=model_name, base_url=settings.OLLAMA_BASE_URL)
    raise ValueError(
        f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER!r}. Choose: openai | anthropic | gemini | ollama"
    )


def _generation_model_name() -> str:
    return {
        "openai": settings.OPENAI_GENERATION_MODEL,
        "anthropic": settings.ANTHROPIC_GENERATION_MODEL,
        "gemini": settings.GOOGLE_GENERATION_MODEL,
        "ollama": settings.OLLAMA_GENERATION_MODEL,
    }[settings.LLM_PROVIDER.lower()]


def _grader_model_name() -> str:
    return {
        "openai": settings.OPENAI_GRADER_MODEL,
        "anthropic": settings.ANTHROPIC_GRADER_MODEL,
        "gemini": settings.GOOGLE_GRADER_MODEL,
        "ollama": settings.OLLAMA_GRADER_MODEL,
    }[settings.LLM_PROVIDER.lower()]


def _get_generation_model() -> BaseChatModel:
    global _generation_model
    if _generation_model is None:
        _generation_model = _make_chat_model(_generation_model_name())
    return _generation_model


def _get_grader_model() -> BaseChatModel:
    global _grader_model
    if _grader_model is None:
        _grader_model = _make_chat_model(_grader_model_name())
    return _grader_model


def _get_embedder():
    global _embedder
    if _embedder is None:
        provider = settings.EMBEDDING_PROVIDER.lower()
        if provider == "openai":
            from langchain_openai import OpenAIEmbeddings
            _embedder = OpenAIEmbeddings(
                model=settings.OPENAI_EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
        elif provider == "gemini":
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            _embedder = GoogleGenerativeAIEmbeddings(
                model=settings.GOOGLE_EMBEDDING_MODEL,
                google_api_key=settings.GOOGLE_API_KEY,
            )
        elif provider == "ollama":
            from langchain_ollama import OllamaEmbeddings
            _embedder = OllamaEmbeddings(
                model=settings.OLLAMA_EMBEDDING_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
            )
        else:
            raise ValueError(
                f"Unsupported EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER!r}. "
                "Choose: openai | gemini | ollama  (Anthropic has no embedding model)"
            )
    return _embedder


# ---------------------------------------------------------------------------
# Message format conversion  (OpenAI-style dicts → LangChain messages)
# ---------------------------------------------------------------------------

def _to_lc_messages(messages: list[dict]) -> list:
    out = []
    for m in messages:
        role, content = m["role"], m["content"]
        if role == "system":
            out.append(SystemMessage(content=content))
        elif role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
    return out


def _extract_usage(response, model_name: str) -> dict:
    meta = getattr(response, "usage_metadata", None) or {}
    return {
        "prompt_tokens": meta.get("input_tokens", 0),
        "completion_tokens": meta.get("output_tokens", 0),
        "total_tokens": meta.get("total_tokens", 0),
        "model": model_name,
    }


# ---------------------------------------------------------------------------
# Public interface  (identical to former openai_client.py — no node changes)
# ---------------------------------------------------------------------------

def generate(messages: list[dict], **kwargs) -> tuple[str, dict]:
    """Call the generation model (high-capability, higher cost)."""
    model = _get_generation_model()
    response = model.invoke(_to_lc_messages(messages), **kwargs)
    return response.content, _extract_usage(response, _generation_model_name())


def grade(messages: list[dict], **kwargs) -> tuple[str, dict]:
    """Call the grader model (faster, cheaper — used by all 5 grader/router nodes)."""
    model = _get_grader_model()
    response = model.invoke(_to_lc_messages(messages), **kwargs)
    return response.content, _extract_usage(response, _grader_model_name())


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts using the configured embedding provider."""
    return _get_embedder().embed_documents(texts)
