import requests
import json
import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

_api = None


def _get_api():
    """Build the PayPal API object once, sandbox only."""
    global _api

    if _api is not None:
        return _api

    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET is missing in .env"
        )

    from paypal_agent_toolkit.openai.toolkit import PayPalToolkit
    from paypal_agent_toolkit.shared.configuration import Configuration, Context

    config = Configuration(
        actions={
            "invoices": {
                "create": True,
                "get": True,
            }
        },
        context=Context(sandbox=True),
    )

    toolkit = PayPalToolkit(client_id, client_secret, config)
    _api = toolkit.get_paypal_api()

    return _api


def _result(
    ok=False,
    invoice_id=None,
    status=None,
    error=None,
    missing=None,
):
    return {
        "ok": ok,
        "invoice_id": invoice_id,
        "status": status,
        "error": error,
        "missing_fields": missing or [],
    }


def _to_dict(raw):
    if isinstance(raw, dict):
        return raw

    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)

            if isinstance(parsed, dict):
                return parsed

            return {"raw": raw}

        except json.JSONDecodeError:
            return {"raw": raw}

    return {"raw": str(raw)}


def _extract_invoice_id(result):
    """Extract invoice ID from PayPal Agent Toolkit response."""

    if not isinstance(result, dict):
        return None

    # Direct ID field
    if result.get("id"):
        return result["id"]

    # Toolkit response: {"createResult": {"href": ".../invoices/INV2-..."}}
    create_result = result.get("createResult")

    if isinstance(create_result, dict):
        href = create_result.get("href", "")

        match = re.search(
            r"/invoices/([A-Za-z0-9\-]+)",
            href or "",
        )

        if match:
            return match.group(1)

    # Fallback: search all href fields
    hrefs = [result.get("href", "")]

    links = result.get("links", [])

    if isinstance(links, list):
        hrefs += [
            link.get("href", "")
            for link in links
            if isinstance(link, dict)
        ]

    for href in hrefs:
        match = re.search(
            r"/invoices/([A-Za-z0-9\-]+)",
            href or "",
        )

        if match:
            return match.group(1)

    # Last fallback: search the raw response text
    raw = result.get("raw", "")

    if raw:
        match = re.search(
            r"/invoices/([A-Za-z0-9\-]+)",
            str(raw),
        )

        if match:
            return match.group(1)

    return None


def create_paypal_invoice(
    client_name,
    amount,
    currency,
    description,
    due_date,
    client_email=None,
):
    """Create a DRAFT invoice in the PayPal sandbox."""

    values = {
        "client_name": client_name,
        "client_email": client_email,
        "amount": amount,
        "currency": currency,
        "description": description,
        "due_date": due_date,
    }

    missing = [
        key
        for key, value in values.items()
        if value in (None, "", [])
    ]

    if missing:
        return _result(
            error="Missing: " + ", ".join(missing),
            missing=missing,
        )

    try:
        amount_dec = Decimal(str(amount))

        if amount_dec <= 0:
            return _result(error="Amount must be greater than 0.")

    except InvalidOperation:
        return _result(error="Amount is not a valid number.")

    currency = str(currency).strip().upper()

    if not re.fullmatch(r"[A-Z]{3}", currency):
        return _result(
            error="Currency must be a 3-letter code like USD."
        )

    try:
        due = datetime.strptime(
            str(due_date),
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return _result(error="Due date must look like YYYY-MM-DD.")

    if due < date.today():
        return _result(error="Due date is in the past.")

    email = str(client_email).strip()

    if not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        email,
    ):
        return _result(error="Customer email address is not valid.")

    parts = str(client_name).strip().split(" ", 1)

    given_name = parts[0]
    surname = parts[1] if len(parts) > 1 else None

    args = {
        "detail": {
            "currency_code": currency,
            "invoice_date": date.today().isoformat(),
        },
        "primary_recipients": [
            {
                "billing_info": {
                    "email_address": email,
                    "name": {
                        "given_name": given_name,
                        "surname": surname,
                    },
                }
            }
        ],
        "items": [
            {
                "name": (
                    f"{str(description).strip()} "
                    f"(Due: {due.isoformat()})"
                )[:200],
                "quantity": "1",
                "unit_amount": {
                    "currency_code": currency,
                    "value": f"{amount_dec:.2f}",
                },
            }
        ],
    }

    try:
        api = _get_api()

        result = _to_dict(
            api.run(
                "create_invoice",
                args,
            )
        )

        logger.info(
            "PayPal create_invoice response: %s",
            result,
        )

        invoice_id = _extract_invoice_id(result)

        if not invoice_id:
            return _result(
                error=(
                    "PayPal did not create the invoice: "
                    f"{result.get('raw') or result}"
                )
            )

        status = "DRAFT"

        try:
            info = _to_dict(
                api.run(
                    "get_invoice",
                    {
                        "invoice_id": invoice_id,
                    },
                )
            )

            status = info.get("status", status)

        except Exception as status_error:
            logger.warning(
                "Could not fetch invoice status: %s",
                status_error,
            )

        return _result(
            ok=True,
            invoice_id=invoice_id,
            status=status,
        )

    except ImportError as import_error:
        return _result(
            error=(
                f"Missing package ({import_error}). "
                "Run: pip install paypal-agent-toolkit openai-agents"
            )
        )

    except Exception as paypal_error:
        return _result(
            error=f"PayPal error: {paypal_error}"
        )


def send_paypal_invoice(invoice_id: str):
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")

    if not client_id or not client_secret:
        return {
            "ok": False,
            "error": (
                "PAYPAL_CLIENT_ID or PAYPAL_CLIENT_SECRET "
                "is missing in .env"
            ),
        }

    try:
        token_url = (
            "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        )

        token_response = requests.post(
            token_url,
            auth=(client_id, client_secret),
            data={
                "grant_type": "client_credentials",
            },
            timeout=30,
        )

        if token_response.status_code != 200:
            return {
                "ok": False,
                "error": (
                    "Could not get PayPal token: "
                    f"{token_response.text}"
                ),
            }

        access_token = token_response.json().get("access_token")

        send_url = (
            "https://api-m.sandbox.paypal.com/v2/invoicing/invoices/"
            f"{invoice_id}/send"
        )

        response = requests.post(
            send_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "send_to_invoicer": True,
                "send_to_recipient": True,
            },
            timeout=30,
        )

        if response.status_code in (200, 202):
            return {
                "ok": True,
                "invoice_id": invoice_id,
                "status": "SENT",
                "error": None,
            }

        return {
            "ok": False,
            "error": response.text,
            "status_code": response.status_code,
        }

    except Exception as error:
        return {
            "ok": False,
            "error": str(error),
        }