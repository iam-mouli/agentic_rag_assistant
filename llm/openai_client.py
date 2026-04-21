from openai import OpenAI
from config.settings import settings

_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate(messages: list, **kwargs) -> tuple[str, dict]:
    model = kwargs.pop("model", settings.OPENAI_GENERATION_MODEL)
    response = _client.chat.completions.create(model=model, messages=messages, **kwargs)
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
        "model": model,
    }
    return response.choices[0].message.content, usage


def grade(messages: list, **kwargs) -> tuple[str, dict]:
    return generate(messages, model=settings.OPENAI_GRADER_MODEL, **kwargs)


def embed(texts: list[str]) -> list[list[float]]:
    response = _client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]
