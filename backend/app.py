from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from docx import Document
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


app = FastAPI()


splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)


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

    return {
        "filename": file.filename,
        "total_chunks": len(documents),
        "documents": documents
    }


@app.post("/web")
async def ingest_web_page(url: str = Form(...)):

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    text = soup.get_text(separator="\n", strip=True)

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

    return {
        "url": url,
        "total_chunks": len(documents),
        "documents": documents
    }