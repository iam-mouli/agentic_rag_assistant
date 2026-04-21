def build_answer_grader_messages(query: str, generation: str) -> list:
    return [
        {
            "role": "system",
            "content": (
                "You are an answer quality grader for a RAG system.\n"
                "Given a user query and a generated answer, score how well "
                "the answer addresses the user's question.\n"
                "A score of 1.0 means the answer fully and directly resolves the query. "
                "A score of 0.0 means the answer is completely irrelevant or unhelpful.\n"
                "Respond with a single float between 0.0 and 1.0. No other text."
            ),
        },
        {
            "role": "user",
            "content": f"Query: {query}\n\nAnswer:\n{generation}",
        },
    ]
