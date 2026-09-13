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
from rank_bm25 import BM25Okapi


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


all_documents = []
bm25 = None


def rebuild_bm25():

    global bm25

    tokenized_documents = [
        document["text"].lower().split()
        for document in all_documents
    ]

    if tokenized_documents:
        bm25 = BM25Okapi(tokenized_documents)


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

    all_documents.extend(documents)

    rebuild_bm25()

    return len(points)


def search_documents(query, top_k=5):

    query_vector = embed_model.get_text_embedding(query)

    results = qdrant_client.query_points(
        collection_name="knowledge_base",
        query=query_vector,
        limit=top_k,
        with_payload=True
    ).points

    documents = []

    for result in results:

        documents.append({
            "id": str(result.id),
            "score": result.score,
            "text": result.payload["text"],
            "metadata": result.payload["metadata"]
        })

    return documents


def search_bm25(query, top_k=5):

    if bm25 is None:
        return []

    query_tokens = query.lower().split()

    scores = bm25.get_scores(query_tokens)

    ranked_indexes = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True
    )[:top_k]

    results = []

    for index in ranked_indexes:

        results.append({
            "id": index,
            "score": float(scores[index]),
            "text": all_documents[index]["text"],
            "metadata": all_documents[index]["metadata"]
        })

    return results


def hybrid_search(query, top_k=5):

    vector_results = search_documents(
        query,
        top_k
    )

    bm25_results = search_bm25(
        query,
        top_k
    )

    rrf_scores = {}
    documents = {}

    k = 60

    for rank, result in enumerate(vector_results):

        document_key = result["text"]

        rrf_scores[document_key] = (
            rrf_scores.get(document_key, 0)
            + 1 / (k + rank + 1)
        )

        documents[document_key] = result

    for rank, result in enumerate(bm25_results):

        document_key = result["text"]

        rrf_scores[document_key] = (
            rrf_scores.get(document_key, 0)
            + 1 / (k + rank + 1)
        )

        documents[document_key] = result

    ranked_documents = sorted(
        rrf_scores,
        key=rrf_scores.get,
        reverse=True
    )[:top_k]

    results = []

    for document_key in ranked_documents:

        document = documents[document_key].copy()

        document["score"] = rrf_scores[document_key]

        results.append(document)

    return results


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


@app.post("/search")
async def search(query: str = Form(...)):

    results = hybrid_search(query)

    return {
        "query": query,
        "results": results
    }