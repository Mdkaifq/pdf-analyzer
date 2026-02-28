# Folder Structure

```
/workspace/
├── README.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── main.py
├── models/
│   ├── __init__.py
│   ├── document.py
│   ├── extraction.py
│   ├── summary.py
│   └── entity.py
├── services/
│   ├── __init__.py
│   ├── document_service.py
│   ├── llm_service.py
│   ├── extraction_service.py
│   ├── summarization_service.py
│   ├── entity_linking_service.py
│   └── anomaly_detection_service.py
├── routers/
│   ├── __init__.py
│   ├── document_router.py
│   └── health_router.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   ├── llm_client.py
│   ├── chunker.py
│   ├── validator.py
│   └── confidence_calculator.py
├── db/
│   ├── __init__.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── document.py
│   └── schemas/
│       ├── __init__.py
│       └── document.py
├── utils/
│   ├── __init__.py
│   ├── helpers.py
│   ├── logger.py
│   └── constants.py
├── tests/
│   ├── __init__.py
│   ├── test_document_processing.py
│   ├── test_extraction.py
│   ├── test_entity_linking.py
│   └── conftest.py
└── docs/
    ├── api_spec.yaml
    └── architecture.md
```