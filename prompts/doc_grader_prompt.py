def build_doc_grader_messages(query: str, chunk: str) -> list:
    return [
        {
            "role": "system",
            "content": (
                "You are a relevance grader for a RAG system.\n"
                "Given a user query and a document chunk, assess whether the chunk "
                "contains information useful for answering the query.\n"
                "The chunk does not need to fully answer the query — "
                "partial relevance is sufficient.\n"
                "Respond with exactly one word: 'yes' or 'no'."
            ),
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nDocument chunk:\n{chunk}",
        },
    ]
