from llm.openai_client import embed as _embed


def embed_texts(texts: list[str]) -> list[list[float]]:
    return _embed(texts)


def embed_query(query: str) -> list[float]:
    return _embed([query])[0]
