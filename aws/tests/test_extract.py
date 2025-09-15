import pytest
import json
from unittest.mock import patch, MagicMock
from extract import extract_text_from_pdf, extract_structured_data, validate_extraction

@patch('boto3.client')
def test_extract_text_from_pdf(mock_client):
    mock_textract = MagicMock()
    mock_response = {'Blocks': [{'BlockType': 'LINE', 'Text': 'Sample text'}]}
    mock_textract.detect_document_text.return_value = mock_response
    mock_client.return_value = mock_textract
    
    pdf_bytes = b'%PDF-1.4...'  # Dummy
    text = extract_text_from_pdf(pdf_bytes)
    assert 'Sample text' in text

def test_extract_structured_data():
    sample_text = "Box 1 Wages: 50000\nBox 2 Federal: 5000"
    extracted = extract_structured_data(sample_text)
    assert "earnings" in extracted
    assert isinstance(extracted["earnings"], dict)

def test_validate_extraction():
    extracted = {"earnings": {"wages": 50000.0}}
    golden = {"earnings": {"wages": 50000.0}}
    validation = validate_extraction(extracted, golden)
    assert validation["overall_accuracy"] == 1.0

# Run with: pytest tests/test_extract.py -v
