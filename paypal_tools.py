import json
import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

load_dotenv()  # read PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET from .env

logger = logging.getLogger(__name__)

_api = None  # cached PayPal API object (Streamlit reruns the script on every click)


def _get_api():
    """Build the PayPal API object once, sandbox only."""
    global _api
    if _api is not None:
        return _api

    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET is missing in .env")

    from paypal_agent_toolkit.openai.toolkit import PayPalToolkit
    from paypal_agent_toolkit.shared.configuration import Configuration, Context

    config = Configuration(
        actions={"invoices": {"create": True, "get": True}},  # only the tools we use
        context=Context(sandbox=True),                        # sandbox is hard-coded
    )
    toolkit = PayPalToolkit(client_id, client_secret, config)
    _api = toolkit.get_paypal_api()
    return _api


def _result(ok=False, invoice_id=None, status=None, error=None, missing=None):
    """Every return path uses this one shape, so app.py can rely on it."""
    return {
        "ok": ok,
        "invoice_id": invoice_id,
        "status": status,
        "error": error,
        "missing_fields": missing or [],
    }


def _to_dict(raw):
    """The toolkit may return a JSON string, a dict, or plain text."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"raw": raw}
        except json.JSONDecodeError:
            return {"raw": raw}
    return {"raw": str(raw)}


def _extract_invoice_id(result):
    """PayPal's create response is often a link ending in /invoices/INV2-XXXX."""
    if result.get("id"):
        return result["id"]
    hrefs = [result.get("href", "")]
    hrefs += [l.get("href", "") for l in result.get("links", []) if isinstance(l, dict)]
    for href in hrefs:
        match = re.search(r"/invoices/([A-Za-z0-9\-]+)", href or "")
        if match:
            return match.group(1)
    return None


def create_paypal_invoice(client_name, amount, currency, description, due_date):
    """Create a DRAFT invoice in the PayPal sandbox.
    Returns {"ok", "invoice_id", "status", "error", "missing_fields"}."""

    # 1) Missing fields: stop before any network call
    values = {
        "client_name": client_name,
        "amount": amount,
        "currency": currency,
        "description": description,
        "due_date": due_date,
    }
    missing = [k for k, v in values.items() if v in (None, "", [])]
    if missing:
        return _result(error="Missing: " + ", ".join(missing), missing=missing)

    # 2) Validate values
    try:
        amount_dec = Decimal(str(amount))
        if amount_dec <= 0:
            return _result(error="Amount must be greater than 0.")
    except InvalidOperation:
        return _result(error="Amount is not a valid number.")

    currency = str(currency).strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        return _result(error="Currency must be a 3-letter code like USD.")

    try:
        due = datetime.strptime(str(due_date), "%Y-%m-%d").date()
    except ValueError:
        return _result(error="Due date must look like YYYY-MM-DD.")
    if due < date.today():
        return _result(error="Due date is in the past.")

    # 3) Build the payload exactly as the create_invoice schema defines it
    parts = str(client_name).strip().split(" ", 1)
    given_name = parts[0]
    surname = parts[1] if len(parts) > 1 else None

    args = {
        "detail": {
            "currency_code": currency,
            "invoice_date": date.today().isoformat(),
        },
        "primary_recipients": [
            {"billing_info": {"name": {"given_name": given_name, "surname": surname}}}
        ],
        "items": [
            {
                # Schema has no due-date field, so it goes in the item name
                "name": f"{str(description).strip()} (Due: {due.isoformat()})"[:200],
                "quantity": "1",
                "unit_amount": {"currency_code": currency, "value": f"{amount_dec:.2f}"},
            }
        ],
    }

    # 4) Call PayPal and turn any failure into an error message
    try:
        api = _get_api()
        result = _to_dict(api.run("create_invoice", args))
        logger.info("PayPal create_invoice response: %s", result)

        invoice_id = _extract_invoice_id(result)
        if not invoice_id:
            return _result(error=f"PayPal did not create the invoice: {result.get('raw') or result}")

        status = "DRAFT"  # new invoices start as drafts
        try:
            info = _to_dict(api.run("get_invoice", {"invoice_id": invoice_id}))
            status = info.get("status", status)
        except Exception as e:
            logger.warning("Could not fetch invoice status: %s", e)

        return _result(ok=True, invoice_id=invoice_id, status=status)

    except ImportError as e:
        return _result(error=f"Missing package ({e}). Run: pip install paypal-agent-toolkit openai-agents")
    except Exception as e:
        return _result(error=f"PayPal error: {e}")