from io import BytesIO
from PyPDF2 import PdfReader
from fastapi import UploadFile, File
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return "Server is runnning"

@app.post("documents")
async def upload_document(file: UploadFile = File(...)):
    doc_bytes = await file.read()
    pdf_stream = BytesIO(doc_bytes)
    reader = PdfReader(pdf_stream)