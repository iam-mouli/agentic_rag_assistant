def build_router_messages(query: str) -> list:
    return [
        {
            "role": "system",
            "content": (
                "You are a query router for an enterprise knowledge base assistant.\n"
                "Decide if the query requires searching the documentation (retrieve) "
                "or can be answered directly from general knowledge (direct_answer).\n"
                "Examples that need retrieval: product-specific configurations, "
                "error codes, feature details, version-specific behavior.\n"
                "Examples for direct answer: greetings, general IT concepts, "
                "simple definitions not tied to a specific product.\n"
                "Respond with exactly one word: 'retrieve' or 'direct_answer'."
            ),
        },
        {"role": "user", "content": f"Query: {query}"},
    ]
