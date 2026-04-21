from langchain_core.documents import Document

from vectorstore.embedder import embed_query
from vectorstore.store import search
from config.constants import TOP_K_RETRIEVAL


def retrieve_chunks(query: str, tenant_id: str, k: int = TOP_K_RETRIEVAL) -> list[Document]:
    embedding = embed_query(query)
    results = search(tenant_id, embedding, k=k)
    return [
        Document(
            page_content=result["text"],
            metadata={
                "doc_id": result.get("doc_id"),
                "tenant_id": result.get("tenant_id"),
                "filename": result.get("filename"),
                "page": result.get("page"),
                "chunk_index": result.get("chunk_index"),
                "score": result.get("score"),
            },
        )
        for result in results
    ]
