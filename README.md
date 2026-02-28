# AI-Powered Document Intelligence API

## Overview

A production-ready backend system that processes documents (PDF/text) to extract structured information, generate hierarchical summaries, detect anomalies, perform cross-page entity linking, and provide confidence scores. Built with Python, FastAPI, and modern AI techniques.

## Architecture Diagram

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Documents     │───▶│  API Gateway     │───▶│   Processing    │
│   (PDF/Text)    │    │  (FastAPI)       │    │   Pipeline      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  PostgreSQL     │◀───│  Application     │◀───│  LLM Service    │
│  (Storage/Cache)│    │  Services        │    │  (OpenAI/Claude)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                            │
                   ┌──────────────────┐
                   │  Background      │
                   │  Tasks           │
                   └──────────────────┘
```

## Features

- **Document Ingestion**: Supports PDF and text files with chunked processing
- **Hierarchical Summarization**: Multi-level summaries (chunk → section → global)
- **Structured Data Extraction**: Strict JSON output with validation and repair loops
- **Entity Linking**: Cross-page entity detection and linking
- **Anomaly Detection**: Hybrid rule-based + LLM anomaly identification
- **Confidence Scoring**: Deterministic scoring combining multiple factors
- **Context Compression**: Sliding window memory for large documents
- **Production Ready**: Dockerized, scalable, monitored

## Tech Stack

- Python 3.11+
- FastAPI (async web framework)
- Pydantic v2 (data validation)
- PostgreSQL (primary database)
- Redis (caching, optional)
- PyMuPDF (PDF processing)
- FAISS (vector similarity)
- httpx (async HTTP client)
- Docker (containerization)

## Setup Instructions

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL server
- LLM API key (OpenAI, Anthropic, etc.)

### Local Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run migrations:
```bash
# Assuming you're using alembic for migrations
alembic upgrade head
```

5. Start the application:
```bash
uvicorn main:app --reload
```

### Docker Deployment

1. Build the image:
```bash
docker build -t doc-intelligence-api .
```

2. Run with docker-compose:
```bash
docker-compose up -d
```

## API Usage Examples

### Upload and Process Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/process" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "config={\"extract_entities\": true, \"generate_summary\": true}"
```

### Response Format

```json
{
  "document_id": "uuid-string",
  "status": "completed",
  "processing_time": 15.23,
  "confidence_score": 0.87,
  "summary": {
    "global_summary": "...",
    "section_summaries": [...],
    "chunk_summaries": [...]
  },
  "extracted_data": {
    "entities": [...],
    "key_points": [...],
    "dates": [...],
    "numerical_values": [...],
    "risks": [...]
  },
  "anomalies": [...],
  "metrics": {
    "total_chunks": 12,
    "tokens_used": 4500,
    "processing_stages": {...}
  }
}
```

## Engineering Decisions

### LLM Interaction Strategy
Given the constraint of stateless APIs without system prompts or tool calling, we implement:
- Pre-structured JSON templates with clear formatting instructions
- Post-processing validation and repair loops
- Context compression techniques for large documents
- Error recovery mechanisms for malformed responses

### Context Compression
For documents exceeding LLM context windows:
- Sliding window memory with relevance scoring
- Chunk prioritization based on semantic importance
- Token budget management across processing stages

### Entity Linking Algorithm
Cross-page entity detection uses:
- Vector similarity (FAISS) for semantic matching
- Fuzzy string matching for variations
- Entity registry with confidence tracking
- Merging rules for duplicate detection

### Confidence Scoring Formula
Final confidence combines:
- Extraction validity (JSON schema compliance)
- Entity consistency (cross-reference validation)
- LLM confidence indicators (where available)
- Repair attempt count (penalizes multiple fixes)

## Scalability Notes

- Asynchronous processing with background tasks
- Database connection pooling
- Redis caching for frequently accessed data
- Horizontal scaling via container orchestration
- Queue-based task distribution for heavy processing

## Production Considerations

- Comprehensive logging and monitoring
- Circuit breaker patterns for external API calls
- Rate limiting and authentication
- Data retention policies
- Backup and disaster recovery procedures

## Resume Positioning

This project demonstrates expertise in:
- Advanced NLP and document processing systems
- Large Language Model integration and optimization
- Production-scale API development with FastAPI
- Complex data pipeline architecture
- Performance optimization and reliability engineering
- Modern DevOps practices with Docker and containerization
- Scalable system design for AI workloads