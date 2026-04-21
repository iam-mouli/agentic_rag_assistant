def build_rewriter_messages(query: str) -> list:
    return [
        {
            "role": "system",
            "content": (
                "You are a query optimizer for a document retrieval system.\n"
                "Rephrase the given query to maximize the chance of retrieving "
                "relevant document chunks via semantic search.\n"
                "Make the query more specific, use domain terminology, "
                "and expand abbreviations if helpful.\n"
                "Return only the rewritten query — no explanation, no preamble."
            ),
        },
        {"role": "user", "content": f"Original query: {query}"},
    ]
