import pytest
import json
from unittest.mock import patch, MagicMock
from extract import extract_text_from_pdf, extract_structured_data, validate_extraction

@patch('azure.ai.documentintelligence.DocumentIntelligenceClient')
def test_extract_text_from_pdf(mock_client):
    mock_poller = MagicMock()
    mock_result = MagicMock()
    mock_page = MagicMock()
    mock_page.lines = [MagicMock(content='Sample text')]
    mock_result.pages = [mock_page]
    mock_poller.result.return_value = mock_result
    mock_client.return_value.begin_analyze_document.return_value = mock_poller
    
    pdf_bytes = b'%PDF-1.4...'  # Dummy
    text = extract_text_from_pdf(pdf_bytes)
    assert 'Sample text' in text

@patch('openai.AzureOpenAI')
def test_extract_structured_data(mock_openai):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"earnings": {"wages": 50000}}'
    mock_response.choices = [mock_choice]
    mock_openai.return_value.chat.completions.create.return_value = mock_response
    
    sample_text = "Box 1 Wages: 50000\nBox 2 Federal: 5000"
    extracted = extract_structured_data(sample_text)
    assert "earnings" in extracted
    assert isinstance(extracted["earnings"], dict)

def test_validate_extraction():
    extracted = {"earnings": {"wages": 50000.0}}
    golden = {"earnings": {"wages": 50000.0}}
    validation = validate_extraction(extracted, golden)
    assert validation["overall_accuracy"] == 1.0