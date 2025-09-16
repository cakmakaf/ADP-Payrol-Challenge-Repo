# Payroll Document Extraction Prototype

This project is a simple prototype for extracting structured data from W-2 forms using AWS Textract for OCR and AWS Bedrock for LLM-based JSON parsing, with a Streamlit WebUI for user interaction.

## System Architecture
The following diagram illustrates the system design:

```mermaid
graph TD
    A[User] -->|Uploads PDF| B(Streamlit WebUI - app.py)
    B -->|PDF Bytes| C[Backend - extract.py]
    C -->|Raw Text Extraction| D[AWS Textract]
    C -->|Text to JSON| E[AWS Bedrock - Claude]
    D -->|Raw Text| C
    E -->|Structured JSON| C
    C -->|Display JSON| B
    C -->|Optional Validation| F[Golden Dataset - golden_sample.json]
    B -->|View Results| A
```

## Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/ADP-Payrol-Challenge-Repo/aws.git
   cd payroll-extraction-prototype
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Required packages: `streamlit==1.28.0`, `boto3==1.34.0`, `requests==2.31.0`, `pytest==7.4.0`.

3. **Configure AWS**:
   - Run `aws configure` and provide your AWS Access Key, Secret Key, and set region to `us-east-1`.
   - Ensure IAM role has permissions for `textract:DetectDocumentText` and `bedrock:InvokeModel`.
   - In AWS Bedrock Console, enable access to `Anthropic Claude v2` (or `Claude 3 Sonnet`).

4. **Sample W-2 PDF**:
   - A sample `sample_w2.pdf` is included. Alternatively, download:
     ```bash
     wget https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf -O sample_w2.pdf
     ```

## Running the App
1. **Start the Streamlit App**:
   ```bash
   streamlit run app.py
   ```
   - Opens a WebUI at `http://localhost:8501`.
   - Upload a W-2 PDF to extract text and structured JSON.
   - Optionally, check "Validate against Golden Sample" to compare with `golden_sample.json`.

2. **Usage**:
   - Upload a W-2 PDF via the WebUI.
   - View extracted text (from Textract) and JSON output (from Bedrock).
   - Download a sample W-2 PDF using the provided button if needed.

## Testing the Model
1. **Run Unit Tests**:
   ```bash
   pytest tests/test_extract.py -v
   ```
   - Tests the `extract_text_from_pdf`, `extract_structured_data`, and `validate_extraction` functions.
   - Uses `pytest` with mocks for AWS calls to ensure offline testing.
   - Verbose mode (`-v`) shows detailed pass/fail results.

2. **Test Details**:
   - `test_extract_text_from_pdf`: Verifies Textract text extraction (mocked).
   - `test_extract_structured_data`: Checks if Bedrock produces structured JSON (requires AWS access or mock).
   - `test_validate_extraction`: Validates accuracy logic against a golden dataset.

3. **Troubleshooting**:
   - If `AccessDeniedException` occurs, ensure IAM permissions and Bedrock model access (`anthropic.claude-v2`).
   - Mock `extract_structured_data` test to avoid AWS calls:
     ```python
     @patch('boto3.client')
     def test_extract_structured_data(mock_client):
         mock_bedrock = MagicMock()
         mock_response = {'body': MagicMock(read=MagicMock(return_value=json.dumps({'completion': '{"earnings": {"wages": 50000}}'})))}
         mock_bedrock.invoke_model.return_value = mock_response
         mock_client.return_value = mock_bedrock
         sample_text = "Box 1 Wages: 50000\nBox 2 Federal: 5000"
         extracted = extract_structured_data(sample_text)
         assert "earnings" in extracted
         assert isinstance(extracted["earnings"], dict)
     ```

## Fields Extracted
- **Employee**: Name, SSN (masked, e.g., XXX-XX-XXXX), address.
- **Employer**: Name, address.
- **Tax Year**: Annual year (e.g., 2023).
- **Earnings**: Wages (Box 1), Social Security wages (Box 3), Medicare wages (Box 5).
- **Deductions**: Federal tax withheld (Box 2), Social Security tax (Box 4), Medicare tax (Box 6), state tax.
- **Net Pay Estimate**: Wages minus total withholdings (approximated).
- **YTD Totals**: Total wages and withheld amounts for the year.

## Limitations
- Assumes US W-2 forms; paychecks require prompt adjustments.
- No multi-page PDF handling beyond Textract limits.
- Basic error handling; no production-grade security or scaling.
- LLM may hallucinate on noisy OCR output.

## Notes
- Ensure Python 3.8+ is installed.
- For production, deploy on AWS EC2/Lambda with S3 for storage.
- Extend with regex validation or multi-document support for robustness.
