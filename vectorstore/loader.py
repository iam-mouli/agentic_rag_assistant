import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config.constants import CHUNK_SIZE, CHUNK_OVERLAP


def compute_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


def load_and_chunk(file_path: str, doc_id: str, tenant_id: str) -> list[Document]:
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(pages)

    filename = Path(file_path).name
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "doc_id": doc_id,
            "tenant_id": tenant_id,
            "filename": filename,
            "chunk_index": i,
        })

    return chunks
