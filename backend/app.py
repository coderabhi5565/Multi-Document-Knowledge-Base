from io import BytesIO
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup
from docx import Document
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from llama_index.embeddings.openai import OpenAIEmbedding
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


app = FastAPI()


splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)


qdrant_client = QdrantClient(
    host="localhost",
    port=6333
)


embed_model = OpenAIEmbedding(
    model="text-embedding-3-small"
)


embedding_dimension = len(
    embed_model.get_text_embedding("dimension check")
)


if not qdrant_client.collection_exists("knowledge_base"):
    qdrant_client.create_collection(
        collection_name="knowledge_base",
        vectors_config=VectorParams(
            size=embedding_dimension,
            distance=Distance.COSINE
        )
    )


def store_documents(documents):

    points = []

    for document in documents:

        vector = embed_model.get_text_embedding(
            document["text"]
        )

        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vector,
                payload={
                    "text": document["text"],
                    "metadata": document["metadata"]
                }
            )
        )

    if points:
        qdrant_client.upsert(
            collection_name="knowledge_base",
            points=points
        )

    return len(points)


@app.get("/")
def root():
    return "Server is running"


@app.post("/documents")
async def upload_document(file: UploadFile = File(...)):

    doc_bytes = await file.read()

    documents = []

    if file.filename.lower().endswith(".pdf"):

        pdf_stream = BytesIO(doc_bytes)
        reader = PdfReader(pdf_stream)

        for page_number, page in enumerate(reader.pages):

            text = page.extract_text()

            if text:

                chunks = splitter.split_text(text)

                for chunk in chunks:

                    documents.append({
                        "text": chunk,
                        "metadata": {
                            "source": file.filename,
                            "page": page_number + 1,
                            "document_type": "pdf"
                        }
                    })

    elif file.filename.lower().endswith(".docx"):

        docx_stream = BytesIO(doc_bytes)
        document = Document(docx_stream)

        full_text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text
        )

        chunks = splitter.split_text(full_text)

        for chunk in chunks:

            documents.append({
                "text": chunk,
                "metadata": {
                    "source": file.filename,
                    "document_type": "docx"
                }
            })

    elif file.filename.lower().endswith(".txt"):

        text = doc_bytes.decode("utf-8")

        chunks = splitter.split_text(text)

        for chunk in chunks:

            documents.append({
                "text": chunk,
                "metadata": {
                    "source": file.filename,
                    "document_type": "txt"
                }
            })

    else:

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Supported types: PDF, DOCX, TXT"
        )

    stored_count = store_documents(documents)

    return {
        "filename": file.filename,
        "total_chunks": len(documents),
        "stored_in_qdrant": stored_count
    }


@app.post("/web")
async def ingest_web_page(url: str = Form(...)):

    async with httpx.AsyncClient() as client:

        response = await client.get(url)

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    text = soup.get_text(
        separator="\n",
        strip=True
    )

    chunks = splitter.split_text(text)

    documents = []

    for chunk in chunks:

        documents.append({
            "text": chunk,
            "metadata": {
                "source": url,
                "document_type": "web"
            }
        })

    stored_count = store_documents(documents)

    return {
        "url": url,
        "total_chunks": len(documents),
        "stored_in_qdrant": stored_count
    }