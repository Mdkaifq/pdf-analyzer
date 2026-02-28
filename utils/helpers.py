import hashlib
import os
import re
from pathlib import Path
from typing import Optional
from .logger import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal and other security issues
    """
    # Remove any directory components
    filename = os.path.basename(filename)
    
    # Keep only alphanumeric characters, dots, underscores, and hyphens
    sanitized = re.sub(r'[^\w\-_.]', '_', filename)
    
    # Limit length to prevent issues
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
    
    return sanitized


def calculate_hash(content: bytes, algorithm: str = 'sha256') -> str:
    """
    Calculate hash of content
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content)
    return hash_obj.hexdigest()


def save_file_securely(content: bytes, base_path: str, filename: str) -> str:
    """
    Save file securely with sanitized filename
    """
    safe_filename = sanitize_filename(filename)
    full_path = os.path.join(base_path, safe_filename)
    
    # Ensure the base path is under the allowed directory
    base_path = os.path.abspath(base_path)
    full_path = os.path.abspath(full_path)
    
    if not full_path.startswith(base_path):
        raise ValueError("Invalid file path")
    
    # Create directory if it doesn't exist
    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Write the file
    with open(full_path, 'wb') as f:
        f.write(content)
    
    logger.info(f"Saved file securely: {full_path}")
    return full_path


def validate_file_type(file_path: str, allowed_extensions: list) -> bool:
    """
    Validate file extension is in allowed list
    """
    _, ext = os.path.splitext(file_path.lower())
    return ext in allowed_extensions


def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes
    """
    return os.path.getsize(file_path)