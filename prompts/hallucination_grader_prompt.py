def build_hallucination_messages(generation: str, documents: list) -> list:
    doc_texts = "\n\n".join(
        f"[doc_id={doc.metadata.get('doc_id', 'unknown')}]\n{doc.page_content}"
        for doc in documents
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a hallucination grader for a RAG system.\n"
                "Given an answer and the source documents it was generated from, "
                "score how well the answer is grounded in the source documents.\n"
                "A score of 1.0 means every claim in the answer is directly supported "
                "by the source documents. A score of 0.0 means the answer contains "
                "claims not present in or contradicted by the sources.\n"
                "Respond with a single float between 0.0 and 1.0. No other text."
            ),
        },
        {
            "role": "user",
            "content": f"Answer:\n{generation}\n\nSource documents:\n{doc_texts}",
        },
    ]
