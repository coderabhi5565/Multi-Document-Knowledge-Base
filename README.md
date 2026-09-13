# Multi-Document Knowledge Base

A production-oriented Retrieval-Augmented Generation (RAG) system that allows users to build a knowledge base from multiple document sources and ask questions over them.

The system supports PDF, DOCX, TXT files, and web pages. It combines keyword-based search (BM25) with semantic vector search, reranks the retrieved results, and generates grounded answers with source attribution.

## Features

- Ingest multiple documents
- Support PDF, DOCX, TXT, and web pages
- Automatic text extraction and chunking
- Store document embeddings in Qdrant
- Semantic vector search
- BM25 keyword search
- Hybrid retrieval using BM25 + vector similarity
- Reranking with Cohere Rerank
- LLM-powered question answering
- Source attribution for generated answers
- React-based user interface
- FastAPI backend

## Architecture

```text
                    React Frontend
                          |
                          v
                    FastAPI Backend
                          |
             +------------+------------+
             |                         |
             v                         v
        Document Ingestion         Query Pipeline
             |                         |
      +------+------+                  |
      |      |      |                  |
     PDF   DOCX   TXT/Web              |
      |      |      |                  |
      +------+------+                  |
             |                         |
             v                         |
        Text Extraction                |
             |                         |
             v                         |
          Chunking                     |
             |                         |
             v                         |
        Embeddings                     |
             |                         |
             v                         |
           Qdrant <--------------------+
             |
             v
       Vector Search
             |
             +------ BM25 Search
             |
             v
       Hybrid Retrieval
             |
             v
       Cohere Rerank
             |
             v
       Relevant Chunks
             |
             v
            LLM
             |
             v
      Answer + Sources
Tech Stack
Backend
Python
FastAPI
LlamaIndex
Retrieval & Storage
Qdrant
BM25
Cohere Rerank
Frontend
React
LLM
OpenAI
Project Structure
multi-document-knowledge-base/
├── backend/
│   └── app.py
├── frontend/
├── requirements.txt
├── .env
├── .gitignore
└── README.md
How It Works
1. Document Ingestion

Users can upload multiple documents or provide web pages.

Document
   ↓
Text Extraction
   ↓
Chunking
   ↓
Metadata
   ↓
Embeddings
   ↓
Qdrant

Each chunk keeps metadata such as its source document and location so that the final answer can be attributed to the correct source.

2. Hybrid Retrieval

When a user asks a question, the system performs two types of retrieval:

Question
   |
   +----> BM25 Search
   |
   +----> Vector Search

BM25 is useful for exact keywords and technical terminology, while vector search is useful for semantic similarity.

The results are combined into a single candidate set.

3. Reranking

The retrieved candidates are passed through Cohere Rerank to improve their relevance to the user's question.

Hybrid Results
      ↓
Cohere Rerank
      ↓
Best Chunks
4. Answer Generation

The highest-quality retrieved chunks are provided to the LLM as context.

Question + Retrieved Context
             ↓
            LLM
             ↓
     Grounded Answer
5. Source Attribution

The system preserves metadata throughout the retrieval pipeline so the final answer can show where the information came from.

Example:

Answer:
Enterprise customers can request a refund within 30 days.

Sources:
- refund_policy.pdf — Page 4
- enterprise_terms.docx — Section: Refunds
