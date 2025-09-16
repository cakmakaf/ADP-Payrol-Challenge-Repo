# Payroll Document Extraction Prototype (Azure)

This project is a simple prototype for extracting structured data from W-2 forms using Azure Document Intelligence for OCR and Azure OpenAI for LLM-based JSON parsing, with a Streamlit WebUI for user interaction.

## System Architecture
The following diagram illustrates the system design:

```mermaid
graph TD
    A[User] -->|Uploads PDF| B(Streamlit WebUI - app.py)
    B -->|PDF Bytes| C[Backend - extract.py]
    C -->|Raw Text Extraction| D[Azure Document Intelligence]
    C -->|Text to JSON| E[Azure OpenAI - GPT]
    D -->|Raw Text| C
    E -->|Structured JSON| C
    C -->|Display JSON| B
    C -->|Optional Validation| F[Golden Dataset - golden_sample.json]
    B -->|View Results| A
```

## Repository Structure
```
payroll-extraction-prototype-azure/
├── app.py                  # Streamlit WebUI for PDF upload and display
├── extract.py              # Core logic: Azure Document Intelligence + OpenAI
├── requirements.txt        # Dependencies for Azure SDKs and Streamlit
├── tests/                  # Unit tests directory
│   └── test_extract.py     # Tests with Azure mocks
├── sample_w2.pdf           # Sample W-2 PDF (to be downloaded)
├── golden_sample.json      # Golden dataset for validation
└── README.md               # This file
```

## Setup Instructions

Follow these steps to set up and run the prototype on your local machine (e.g., `/../Desktop/ADP-Payrol-Challenge/azure`).

### 1. Create the Repository
- Create a directory and initialize a Git repository (optional for GitHub):
  ```bash
  mkdir /.../Desktop/ADP-Payrol-Challenge-Azure
  cd /.../Desktop/ADP-Payrol-Challenge-Azure
  git init
  ```

### 2. Create Files
Create the following files with the specified contents using a text editor (e.g., `nano`, VS Code).

#### `requirements.txt`
```text
streamlit==1.28.0
azure-ai-documentintelligence==1.0.0b1
openai==1.3.0
requests==2.31.0
pytest==7.4.0
```

#### `app.py`
```python
import streamlit as st
import io
from extract import extract_text_from_pdf, extract_structured_data, validate_extraction
import json

st.title("W-2 Document Extraction Prototype (Azure)")

uploaded_file = st.file_uploader("Upload W-2 PDF", type="pdf")

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    text = extract_text_from_pdf(pdf_bytes)
    st.text_area("Extracted Text (Preview)", text, height=200)
    
    with st.spinner("Extracting structured data..."):
        extracted = extract_structured_data(text)
    
    st.subheader("Extracted JSON")
    st.json(extracted)
    
    # Optional Validation
    if st.checkbox("Validate against Golden Sample"):
        with open("golden_sample.json", "r") as f:
            golden = json.load(f)
        validation = validate_extraction(extracted, golden)
        st.subheader("Validation Results")
        st.json(validation)

# Download Sample
if st.button("Download Sample W-2 PDF"):
    import requests
    url = "https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf"
    response = requests.get(url)
    st.download_button("Download", response.content, "sample_w2.pdf", "application/pdf")
```

#### `extract.py`
```python
import os
from typing import Dict, Any
import json
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import AnalyzeResult
from openai import AzureOpenAI

# Azure Clients (use env vars for auth)
document_intelligence_client = DocumentIntelligenceClient(
    endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"))
)

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-02-15-preview"
)

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Preprocess: Use Azure Document Intelligence to extract text from PDF."""
    poller = document_intelligence_client.begin_analyze_document(
        "prebuilt-layout",  # Model for layout/text extraction
        analyze_request={"url": None},  # Local bytes
        content_type="application/pdf",
        bytes_source=pdf_bytes  # Pass PDF bytes
    )
    result: AnalyzeResult = poller.result()
    text = ''
    for page in result.pages:
        for line in page.lines:
            text += line.content + '\n'
    return text.strip()

def extract_structured_data(text: str) -> Dict[str, Any]:
    """LLM Extraction: Use Azure OpenAI (GPT) with prompt engineering to parse JSON."""
    prompt = f"""
    You are an expert at extracting data from W-2 forms. Parse the following text and output ONLY valid JSON with these fields:
    {{
        "employee": {{
            "name": "str",
            "ssn": "str (masked, e.g., XXX-XX-XXXX)",
            "address": "str"
        }},
        "employer": {{
            "name": "str",
            "address": "str"
        }},
        "tax_year": "str",
        "earnings": {{
            "wages": "float (box 1)",
            "social_security_wages": "float (box 3)",
            "medicare_wages": "float (box 5)"
        }},
        "deductions": {{
            "federal_tax": "float (box 2)",
            "social_security_tax": "float (box 4)",
            "medicare_tax": "float (box 6)",
            "state_tax": "float (state section)"
        }},
        "net_pay_estimate": "float (wages - total withholdings)",
        "ytd_totals": {{
            "total_wages": "float",
            "total_withheld": "float"
        }}
    }}
    If a field is missing, use null. Be precise with numbers.

    Text: {text}
    """
    
    response = openai_client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),  # e.g., "gpt-35-turbo"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Low for structured output
        max_tokens=1000
    )
    extracted_json = json.loads(response.choices[0].message.content)
    return extracted_json

def validate_extraction(extracted: Dict[str, Any], golden: Dict[str, Any] = None) -> Dict[str, float]:
    """Optional Eval: Simple field-level accuracy."""
    if not golden:
        return {"status": "No golden dataset provided"}
    
    accuracy = {}
    for key in extracted:
        if isinstance(extracted[key], dict):
            sub_acc = {}
            for subkey in extracted[key]:
                val = extracted[key][subkey]
                gold_val = golden[key][subkey]
                if isinstance(val, str):
                    sub_acc[subkey] = 1.0 if val.lower() == gold_val.lower() else 0.0
                elif isinstance(val, float):
                    sub_acc[subkey] = 1.0 if abs(val - gold_val) / gold_val < 0.01 else 0.0
                else:
                    sub_acc[subkey] = 0.0
            accuracy[key] = sum(sub_acc.values()) / len(sub_acc)
        else:
            accuracy[key] = 1.0 if str(extracted[key]).lower() == str(golden[key]).lower() else 0.0
    
    overall_precision = sum(accuracy.values()) / len(accuracy)
    return {"overall_accuracy": overall_precision, "field_accuracies": accuracy}
```

#### `tests/test_extract.py`
```python
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
```

#### `golden_sample.json`
```json
{
    "employee": {
        "name": "John Doe",
        "ssn": "XXX-XX-1234",
        "address": "123 Main St, Anytown, USA"
    },
    "employer": {
        "name": "ABC Corp",
        "address": "456 Business Ave, City, USA"
    },
    "tax_year": "2023",
    "earnings": {
        "wages": 45146.22,
        "social_security_wages": 45146.22,
        "medicare_wages": 45146.22
    },
    "deductions": {
        "federal_tax": 3109.56,
        "social_security_tax": 2799.07,
        "medicare_tax": 655.12,
        "state_tax": 1500.00
    },
    "net_pay_estimate": 35082.47,
    "ytd_totals": {
        "total_wages": 45146.22,
        "total_withheld": 10063.75
    }
}
```

#### Create `tests/` Directory
```bash
mkdir tests
```

### 3. Install Dependencies
- Install required packages:
  ```bash
  pip install -r requirements.txt
  ```

### 4. Configure Azure
- **Install Azure CLI** (if not installed):
  ```bash
  curl -L https://aka.ms/InstallAzureCli | bash
  az login
  ```
- **Create Azure Resources** (in Azure Portal, region: `eastus`):
  - **Document Intelligence**:
    - Search "Document Intelligence" > Create > Standard tier.
    - Copy endpoint (e.g., `https://<your-resource>.cognitiveservices.azure.com/`) and key (from "Keys and Endpoint").
  - **Azure OpenAI**:
    - Search "Azure OpenAI" > Create > Deploy model (e.g., `gpt-35-turbo`).
    - Copy endpoint (e.g., `https://<your-openai>.openai.azure.com/`) and API key.
- **Set Environment Variables**:
  ```bash
  export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://<your-resource>.cognitiveservices.azure.com/"
  export AZURE_DOCUMENT_INTELLIGENCE_KEY="<your-key>"
  export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
  export AZURE_OPENAI_API_KEY="<your-key>"
  export AZURE_OPENAI_DEPLOYMENT="gpt-35-turbo"
  ```
  - Persist in `~/.zshrc` (or `~/.bashrc`):
    ```bash
    echo 'export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://<your-resource>.cognitiveservices.azure.com/"' >> ~/.zshrc
    echo 'export AZURE_DOCUMENT_INTELLIGENCE_KEY="<your-key>"' >> ~/.zshrc
    echo 'export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"' >> ~/.zshrc
    echo 'export AZURE_OPENAI_API_KEY="<your-key>"' >> ~/.zshrc
    echo 'export AZURE_OPENAI_DEPLOYMENT="gpt-35-turbo"' >> ~/.zshrc
    source ~/.zshrc
    ```

### 5. Download Sample W-2 PDF
- Download the sample PDF:
  ```bash
  wget https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf -O sample_w2.pdf
  ```
- If `wget` fails, manually download from [ADP W-2 sample](https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf).

## Running the App
1. **Start the Streamlit App**:
   ```bash
   streamlit run app.py
   ```
   - Opens at `http://localhost:8501`.
   - Upload `sample_w2.pdf` to extract text (Azure Document Intelligence) and structured JSON (Azure OpenAI).
   - Check "Validate against Golden Sample" to compare with `golden_sample.json`.

2. **Usage**:
   - Upload a W-2 PDF via the WebUI.
   - View extracted text in a textarea and JSON output below.
   - Use the "Download Sample W-2 PDF" button if needed.

## Testing the Model
1. **Run Unit Tests**:
   ```bash
   pytest tests/test_extract.py -v
   ```
   - Runs three tests: `test_extract_text_from_pdf`, `test_extract_structured_data`, `test_validate_extraction`.
   - Uses mocks to avoid real Azure API calls, ensuring offline testing.
   - Verbose mode (`-v`) shows pass/fail details.

2. **Test Details**:
   - `test_extract_text_from_pdf`: Verifies text extraction from a mocked Document Intelligence response.
   - `test_extract_structured_data`: Checks JSON output from a mocked OpenAI response.
   - `test_validate_extraction`: Validates accuracy logic against a golden dataset.

## Fields Extracted
- **Employee**: Name, SSN (masked, e.g., XXX-XX-XXXX), address.
- **Employer**: Name, address.
- **Tax Year**: e.g., 2023.
- **Earnings**: Wages (Box 1), Social Security wages (Box 3), Medicare wages (Box 5).
- **Deductions**: Federal tax withheld (Box 2), Social Security tax (Box 4), Medicare tax (Box 6), state tax.
- **Net Pay Estimate**: Wages minus total withholdings (approximated).
- **YTD Totals**: Total wages and withheld amounts for the year.

## Troubleshooting
- **Authentication Errors**:
  - Verify env vars:
    ```bash
    echo $AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
    echo $AZURE_OPENAI_API_KEY
    ```
  - Ensure Azure resources exist and endpoints/keys match.
  - Recheck `az login` status.
- **Dependency Issues**:
  - If `pip install` fails:
    ```bash
    pip install --force-reinstall azure-ai-documentintelligence==1.0.0b1 openai==1.3.0
    ```
- **PDF Download Fails**:
  - Manually download from [ADP W-2 sample](https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf).
- **Test Failures**:
  - Mocks should prevent API errors. If tests fail, check `tests/test_extract.py` for correct mock setup.
- **Streamlit Errors**:
  - Ensure Python 3.12 and all dependencies are installed.
  - Check terminal logs for specific errors (e.g., missing `golden_sample.json`).

## Limitations
- Assumes US W-2 forms; paychecks require prompt adjustments.
- Basic error handling; no multi-page PDF support beyond service limits.
- LLM accuracy varies; GPT-4 (if available) improves over GPT-3.5-turbo.
- Requires Azure subscription (free tier may suffice for testing).

## Notes
- **Python Version**: Requires Python 3.8+ (tested with 3.12).
- **Production Deployment**: Use Azure App Service or Functions for scalability.
- **Enhancements**: Train a custom Document Intelligence model for W-2 specifics or add regex validation.
- **Git Integration** (optional):
  ```bash
  git add .
  git commit -m "Initial Azure-based prototype"
  git remote add origin https://github.com/yourusername/ADP-Payrol-Challenge/azure.git
  git push -u origin main
  ```
