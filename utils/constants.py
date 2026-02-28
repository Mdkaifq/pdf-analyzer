# Constants for the AI-Powered Document Intelligence API

# Common file extensions
ALLOWED_FILE_EXTENSIONS = ['.pdf', '.txt', '.docx', '.csv']

# Default configuration values
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
DEFAULT_CHUNK_SIZE = 2000
DEFAULT_OVERLAP_SIZE = 200

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.8
MEDIUM_CONFIDENCE_THRESHOLD = 0.6
LOW_CONFIDENCE_THRESHOLD = 0.4

# Processing stages
PROCESSING_STAGES = [
    'upload',
    'validation', 
    'chunking',
    'extraction',
    'summarization',
    'entity_linking',
    'anomaly_detection',
    'validation',
    'storage'
]

# Default schema for extracted data
EXTRACTED_DATA_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "entity_type": {"type": "string"},
                    "entity_value": {"type": "string"},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "position_start": {"type": "number"},
                    "position_end": {"type": "number"},
                    "page_number": {"type": "number"},
                    "chunk_index": {"type": "number"},
                    "metadata": {"type": "object"}
                },
                "required": ["entity_type", "entity_value", "confidence_score"]
            }
        },
        "key_points": {
            "type": "array",
            "items": {"type": "string"}
        },
        "dates": {
            "type": "array",
            "items": {"type": "string"}  # ISO format
        },
        "numerical_values": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["value", "context"]
            }
        },
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "risk_type": {"type": "string"},
                    "description": {"type": "string"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "confidence_score": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["risk_type", "description", "severity"]
            }
        }
    },
    "required": ["entities", "key_points", "dates", "numerical_values", "risks"]
}