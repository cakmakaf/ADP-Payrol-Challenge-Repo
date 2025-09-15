# W-2 Document Extraction Prototype (AWS & Azure)

This repository contains two implementations of a W-2 form extraction prototype using Streamlit for the WebUI, with OCR and LLM-based JSON parsing. The `aws/` directory uses AWS Textract and Bedrock (Claude), while the `azure/` directory uses Azure Document Intelligence and OpenAI (GPT).

## System Architecture
Both solutions follow this flow, with different services for OCR and LLM:

```mermaid
graph TD
    A[User] -->|Uploads PDF| B(Streamlit WebUI - app.py)
    B -->|PDF Bytes| C[Backend - extract.py]
    C -->|Raw Text Extraction| D[AWS Textract / Azure Document Intelligence]
    C -->|Text to JSON| E[AWS Bedrock - Claude / Azure OpenAI - GPT]
    D -->|Raw Text| C
    E -->|Structured JSON| C
    C -->|Display JSON| B
    C -->|Optional Validation| F[Golden Dataset - golden_sample.json]
    B -->|View Results| A
```

## Repository Structure
```
ADP-Payrol-Challenge/
├── aws/                    # AWS-based solution
└── azure/                  # Azure-based solution
```

## AWS Solution Setup & Usage
1. **Navigate**:
   ```bash
   cd aws
   ```
2. **Setup**:
   - Install dependencies: `pip install -r requirements.txt`
   - Configure AWS CLI: `aws configure` (region: `us-east-1`)
   - Enable Bedrock model access (Claude v2) in AWS Console
   - Download sample PDF:
     ```bash
     wget https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf -O sample_w2.pdf
     ```
3. **Run**:
   ```bash
   streamlit run app.py
   ```
   - Opens `http://localhost:8501`. Upload PDF to extract JSON.
4. **Test**:
   ```bash
   pytest tests/test_extract.py -v
   ```
5. **Details**: See `aws/README.md`

## Azure Solution Setup & Usage
1. **Navigate**:
   ```bash
   cd azure
   ```
2. **Setup**:
   - Install dependencies: `pip install -r requirements.txt`
   - Install Azure CLI: `curl -L https://aka.ms/InstallAzureCli | bash`
   - Log in: `az login`
   - Create Azure resources (Document Intelligence, OpenAI) in Portal (region: `eastus`)
   - Set env vars:
     ```bash
     export AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT="https://<your-resource>.cognitiveservices.azure.com/"
     export AZURE_DOCUMENT_INTELLIGENCE_KEY="<your-key>"
     export AZURE_OPENAI_ENDPOINT="https://<your-openai>.openai.azure.com/"
     export AZURE_OPENAI_API_KEY="<your-key>"
     export AZURE_OPENAI_DEPLOYMENT="gpt-35-turbo"
     ```
   - Download sample PDF:
     ```bash
     wget https://support.adp.com/adp_payroll/content/hybrid/PDF/W2_Interactive.pdf -O sample_w2.pdf
     ```
3. **Run**:
   ```bash
   streamlit run app.py
   ```
   - Opens `http://localhost:8501`. Upload PDF to extract JSON.
4. **Test**:
   ```bash
   pytest tests/test_extract.py -v
   ```
5. **Details**: See `azure/README.md`

## Fields Extracted
- **Employee**: Name, SSN (masked), address
- **Employer**: Name, address
- **Tax Year**: e.g., 2023
- **Earnings**: Wages (Box 1), Social Security/Medicare wages
- **Deductions**: Federal/SS/Medicare/state taxes
- **Net Pay Estimate**: Wages minus withholdings
- **YTD Totals**: Total wages/withheld

## Troubleshooting
- **AWS**:
  - `AccessDeniedException`: Add IAM permissions (`bedrock:InvokeModel`, `textract:DetectDocumentText`). Enable Claude v2 in Bedrock Console.
- **Azure**:
  - Auth errors: Verify env vars (`echo $AZURE_OPENAI_API_KEY`) and Azure resource setup.
- **General**: Ensure Python 3.8+, check sub-READMEs for detailed fixes.

## Notes
- Both solutions use Streamlit for the UI and produce JSON output.
- See `aws/` or `azure/` for full setup, testing, and deployment details.
- For production, deploy on AWS EC2/Lambda or Azure App Service.