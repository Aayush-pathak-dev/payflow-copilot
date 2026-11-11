# PayFlow Copilot

### From plain English to PayPal Sandbox invoices—with human confirmation.

PayFlow Copilot helps users create invoices through a conversational interface instead of manually filling out invoice forms.

Enter a request, review the extracted details, and confirm the action. The app uses the PayPal Agent Toolkit to create and send a Sandbox invoice, displays the result, and records the attempt in SQLite.

> Development prototype. Uses PayPal Sandbox credentials. Not intended for production financial transactions.

---

## Example

```text
Create a 250 USD invoice for Rahul Sharma at customer@example.com
for 10 hours of web design, due in 7 days.
```

PayFlow extracts:

```json
{
  "action": "create_invoice",
  "client_name": "Rahul Sharma",
  "client_email": "customer@example.com",
  "amount": 250,
  "currency": "USD",
  "description": "10 hours of web design",
  "due_date": "YYYY-MM-DD"
}
```

After the user reviews and confirms the details, the app submits the request to PayPal Sandbox.

An example successful application response:

```json
{
  "ok": true,
  "invoice_id": "INV2-...",
  "status": "SENT",
  "error": null,
  "missing_fields": []
}
```

The actual due date is calculated from the request and current date.

---

## Why PayFlow Copilot?

Creating an invoice involves translating a business request into structured fields: customer, email, amount, currency, description, and payment deadline.

PayFlow brings those steps into one conversational workflow while keeping the user in control of the final action.

The goal is straightforward:

**Describe the work. Review the details. Confirm the invoice.**

---

## Current Features

- Chat-style Streamlit interface
- Natural-language extraction of invoice details
- Groq as the primary AI provider
- Google Gemini fallback when the primary request fails
- Customer email extraction
- Required-field and basic email checks before invoice creation
- Positive-amount, currency-format, and date validation
- Human confirmation before submitting the invoice
- PayPal Sandbox integration through the PayPal Agent Toolkit
- Invoice ID and result display
- SQLite activity logging

### Verified workflow

The current integration has been tested through:

1. Entering an invoice request with a recipient email.
2. Reviewing the extracted details.
3. Confirming the invoice action.
4. Receiving a successful response and invoice ID.
5. Finding the invoice in the PayPal Sandbox business account.
6. Checking the invoice's due date.
7. Confirming that the action was recorded in SQLite.

USD is the tested baseline. Other currencies are not yet presented as verified functionality.

---

## How It Works

```text
Plain-English request
        |
        v
AI extracts structured invoice details
        |
        v
Application checks required details
        |
        v
User reviews and confirms
        |
        v
PayPal Agent Toolkit processes the invoice
        |
        v
Application displays the invoice result
        |
        v
SQLite records the attempt and response
```

### Creation and sending

In the toolkit path tested by this project, invoice creation with a recipient email returned both creation and sending results.

The interface therefore does not perform an additional send action after that successful operation. This avoids attempting to send an already-sent invoice.

Do not assume every toolkit version or configuration behaves identically. Check the returned result and verify the invoice in Sandbox when modifying the integration.

---

## Technology Stack

| Component | Technology |
|---|---|
| User interface | Streamlit |
| Primary AI provider | Groq |
| Fallback AI provider | Google Gemini |
| PayPal integration | PayPal Agent Toolkit |
| Supporting SDK | OpenAI Agents SDK |
| HTTP requests | Requests |
| Activity storage | SQLite |
| Environment configuration | python-dotenv |
| Application language | Python |

The OpenAI Agents SDK is a dependency used by the toolkit integration. Its presence does not mean OpenAI is the application's primary extraction provider.

---

## Project Structure

```text
payflow-copilot/
├── app.py                  # Interface, confirmation, and result handling
├── agent.py                # AI extraction and provider fallback
├── paypal_tools.py         # PayPal integration and validation
├── database.py             # SQLite activity logging
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── .gitignore              # Excluded local files
├── .env                    # Local credentials; never commit
└── payflow_activity.db     # Local activity database
```

The database file is generated or used by the logging code; it should not be committed with test-customer data.

---

## Prerequisites

- Python 3.11 or newer
- A PayPal Developer account
- A PayPal Sandbox business account and REST app credentials
- A Groq API key
- A Gemini API key for the fallback provider

The current client-initialization code may require both AI-provider credentials at startup.

---

## Local Setup

### 1. Open the project

After cloning your repository, enter its directory:

```bash
cd payflow-copilot
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Linux, macOS, or GitHub Codespaces:

```bash
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If your existing environment is named `venv` instead of `.venv`, use that directory consistently.

### 3. Install dependencies

If the repository includes a maintained requirements file:

```bash
python -m pip install -r requirements.txt
```

Otherwise, install the packages currently used by the application:

```bash
python -m pip install streamlit python-dotenv groq google-genai requests paypal-agent-toolkit openai-agents
```

### 4. Configure credentials

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key

PAYPAL_CLIENT_ID=your_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_sandbox_client_secret
```

Use Sandbox credentials, not Live credentials.

Do not put actual keys in source files, screenshots, demo recordings, or this README.

### 5. Run the application

```bash
python -m streamlit run app.py
```

Open the address printed in the terminal.

When using GitHub Codespaces, open the forwarded Streamlit port through the Ports panel.

---

## PayPal Sandbox Configuration

1. Sign in to the PayPal Developer Dashboard.
2. Open Apps & Credentials.
3. Select Sandbox.
4. Create or select a REST application associated with a Sandbox business account.
5. Copy its Client ID and Client Secret into `.env`.
6. Restart the application after changing credentials.

### Inspecting a test invoice

1. In the Developer Dashboard, open Testing Tools → Sandbox Accounts.
2. Find the business account associated with your REST application.
3. View its Sandbox login credentials.
4. Sign in to `sandbox.paypal.com` using that Sandbox account.
5. Open the Invoicing section.
6. Locate the invoice and verify its recipient, amount, currency, and due date.

The Sandbox business login is different from the REST application's Client ID and Client Secret.

---

## Using the App

### Create an invoice

Enter a complete request:

```text
Create a 25 USD invoice for Test Customer at customer@example.com
for website testing, due in 7 days.
```

Use a Sandbox test-customer email you control when testing.

### Review the extracted fields

Check:

- Customer name
- Customer email
- Amount
- Currency
- Description
- Due date

If the details are incorrect, cancel instead of confirming.

### Confirm once

Click the confirmation button once and wait for the result.

The tested toolkit flow can create and send the invoice in the same operation. Do not add a second send action without checking whether the invoice has already been sent.

### Verify the result

Use the returned invoice ID to identify the operation, then inspect the corresponding invoice in the Sandbox business account.

An application success message is not proof that a customer has paid.

---

## Activity Logging

The application records invoice attempts and responses in:

```text
payflow_activity.db
```

The activity table is:

```text
activity_log
```

### View recent actions

Run this from the project root:

```bash
python -c "import sqlite3; c=sqlite3.connect('payflow_activity.db'); print(c.execute('SELECT id, created_at, action FROM activity_log ORDER BY id DESC LIMIT 5').fetchall())"
```

Example:

```text
[(23, '2026-11-10T11:38:27.478988+00:00', 'create_invoice')]
```

### Important distinction

An activity row records an attempt. It does not, by itself, establish that the PayPal operation succeeded.

Inspect the stored response and the PayPal invoice when determining the outcome.

Older logs may contain `send_invoice` entries from an earlier two-step implementation. The current tested flow does not require a separate send action after successful toolkit creation and sending.

---

## Testing Checklist

### Successful invoice request

- [ ] Enter a complete request with a test email.
- [ ] Check the extracted details.
- [ ] Confirm once.
- [ ] Verify the returned invoice ID and result.
- [ ] Open the invoice in PayPal Sandbox.
- [ ] Check the recipient, amount, currency, and due date.
- [ ] Confirm a new activity entry exists.

### Missing email

- [ ] Enter a request without a recipient email.
- [ ] Confirm that the app requests the missing information.
- [ ] Confirm that no PayPal invoice is created.

### Cancellation

- [ ] Enter a complete request.
- [ ] Click Cancel.
- [ ] Confirm that the pending request clears without a PayPal action.

### Error handling

- [ ] Verify missing credentials produce a useful message.
- [ ] Verify AI-provider failures do not trigger invoice creation.
- [ ] Verify PayPal errors remain visible rather than being reported as success.

---

## Troubleshooting

### A package is missing

Install dependencies using the same Python environment that runs Streamlit:

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Common package/import pairs:

| Import | Package |
|---|---|
| `from groq import Groq` | `groq` |
| `from google import genai` | `google-genai` |
| `from agents import Agent, Runner` | `openai-agents` |
| `paypal_agent_toolkit` | `paypal-agent-toolkit` |

### The editor says an import cannot be resolved, but the terminal import works

Select the project's virtual environment using:

```text
Python: Select Interpreter
```

If necessary, reload the editor window afterward.

### PayPal credentials are missing

Check that `.env` contains:

```env
PAYPAL_CLIENT_ID=...
PAYPAL_CLIENT_SECRET=...
```

Restart the app after editing the file.

### `MISSING_RECIPIENT_EMAIL`

Check the complete email flow:

```text
User request
→ extracted client_email
→ create_paypal_invoice(client_email=...)
→ PayPal recipient billing information
```

The recipient payload must include:

```python
"primary_recipients": [
    {
        "billing_info": {
            "email_address": client_email
        }
    }
]
```

Adding an email to the AI prompt alone is not sufficient if it is never passed to PayPal.

### `INVOICE_ALREADY_SENT`

The invoice has already been sent.

Do not repeatedly submit the same send action. Check whether the toolkit's creation response already contains a sending result.

### PayPal created an invoice, but the app reports no invoice ID

Inspect the returned structure.

The tested toolkit has returned a nested creation result:

```json
{
  "createResult": {
    "href": ".../invoices/INV2-..."
  },
  "sendResult": "..."
}
```

Invoice-ID extraction must handle the nested creation link, not only a top-level `id`.

### Groq: `'list' object has no attribute 'message'`

Check the response-access line:

```python
response.choices.message.content
```

If it already matches, inspect the full traceback to locate the actual failing line.

### Gemini returns `503 UNAVAILABLE`

The fallback service is temporarily unavailable.

Do not change the PayPal integration to address an AI-provider availability error. Inspect the primary-provider error separately and retry later when appropriate.

### `no such table: activity_log`

Check that:

- You are inspecting the database used by the app.
- Your terminal is in the expected project directory.
- Database initialization and logging have run.

Opening a relative SQLite path from another directory can point to a different file.

---

## Security and Privacy

- Keep credentials in environment variables.
- Never commit `.env`.
- Use Sandbox credentials while developing.
- Keep customer data and local databases out of the repository.
- Review staged changes before committing.
- Rotate credentials if they are exposed.
- Do not deploy this prototype publicly without reviewing access control and data handling.

Suggested `.gitignore` entries:

```gitignore
.env
.venv/
venv/
__pycache__/
*.pyc
payflow_activity.db
payflow_activity.db-*
```

If a secret has already been committed, adding it to `.gitignore` does not remove it from repository history.

---

## Current Limitations

- Development prototype, not a production-ready billing platform.
- USD is the tested currency baseline.
- Other currencies require validation and account-specific testing.
- AI extraction can make mistakes; user review remains necessary.
- JSON output mode does not replace application-level field validation.
- Dates and payment terms should be checked in PayPal when changing the integration.
- The activity log is not a payment ledger.
- No verified automatic payment-status tracking.
- No authentication or multi-user data isolation.
- Toolkit behavior and response structures can vary by version.
- A reported sent status does not establish payment or inbox delivery.

---

## Roadmap

- [ ] Activity-history panel
- [ ] Clear distinction between successful and failed attempts
- [ ] Invoice lookup and status refresh
- [ ] Validated multi-currency handling
- [ ] Explicit payment-terms handling
- [ ] Automated validation and cancellation tests
- [ ] Dependency-version pinning
- [ ] Improved user-facing error messages
- [ ] Authentication and per-user data isolation
- [ ] Deployment hardening

---

## Project Status

The current tested milestone supports:

```text
Natural-language request
→ AI extraction
→ Human confirmation
→ PayPal Sandbox invoice creation and sending
→ Result display
→ SQLite activity logging
```

The invoice has also been checked in PayPal Sandbox, including its displayed due date.
