import streamlit as st
import json

from agent import interpret_request
from paypal_tools import create_paypal_invoice
from database import log_activity,get_recent_activity


st.set_page_config(
    page_title="PayFlow Copilot",
    page_icon="💸",
    layout="centered",
)


st.title("💸 PayFlow Copilot")
st.caption("Turn plain English into PayPal invoice actions.")
st.warning("PayPal Sandbox — no real money is moved.", icon="⚠️")


# Initialize memory
if "chat" not in st.session_state:
    st.session_state.chat = []

if "pending_invoice" not in st.session_state:
    st.session_state.pending_invoice = None

if "created_invoice_id" not in st.session_state:
    st.session_state.created_invoice_id = None


# Show previous chat messages
for message in st.session_state.chat:
    with st.chat_message(message["role"]):
        st.write(message["content"])


user_input = st.chat_input(
    "Try: Create a $250 invoice for Rahul Sharma at rahul@example.com "
    "for 10 hours of web design, due in 7 days"
)


# When user sends a new message
if user_input:
    st.session_state.chat.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Understanding your request..."):
            try:
                result = interpret_request(user_input)
                result = result.strip()

                if result.startswith("```"):
                    result = result.strip("`")

                    if result.lower().startswith("json"):
                        result = result[4:].strip()

                data = json.loads(result)

            except Exception as error:
                data = {
                    "action": "unknown",
                    "confirmation_message": (
                        f"Sorry, I could not process that request. Error: {error}"
                    ),
                }

        st.write(data.get("confirmation_message", ""))

        if data.get("action") == "create_invoice":
            st.session_state.pending_invoice = data
            st.success("Please confirm the invoice details below.")

            st.json(
                {
                    "Client": data.get("client_name"),
                    "Email": data.get("client_email"),
                    "Amount": data.get("amount"),
                    "Currency": data.get("currency"),
                    "Description": data.get("description"),
                    "Due date": data.get("due_date"),
                }
            )

        elif data.get("action") == "missing_info":
            st.warning("Please include the customer's email address.")
            st.info(
                "Example: Create a $250 invoice for Rahul Sharma at "
                "rahul@example.com for 10 hours of web design, due in 7 days."
            )

        else:
            st.info("Please provide the missing invoice details.")

    st.session_state.chat.append(
        {
            "role": "assistant",
            "content": data.get("confirmation_message", ""),
        }
    )
# Activity history
st.subheader("Activity history")

try:
    activity_rows = get_recent_activity(limit=20)
except Exception as exc:
    st.warning("Could not load activity history.")
    st.caption(str(exc))
else:
    if not activity_rows:
        st.info("No activity recorded yet.")
    else:
        history = []

        for row in activity_rows:
            try:
                response_data = json.loads(row.get("paypal_response") or "{}")
            except (TypeError, ValueError):
                response_data = {}

            ok = bool(response_data.get("ok"))
            invoice_id = response_data.get("invoice_id") or ""
            error = response_data.get("error") or ""

            if ok:
                result = "Success"
            elif error:
                result = "Failed"
            else:
                result = "Recorded"

            history.append(
                {
                    "Time": row.get("created_at", ""),
                    "Action": row.get("action", ""),
                    "Result": result,
                    "Invoice ID": invoice_id,
                    "Request": row.get("user_request", ""),
                    "Error": error,
                }
            )

        st.dataframe(
            history,
            use_container_width=True,
            hide_index=True,
        )

# Confirmation section survives Streamlit reruns
if st.session_state.pending_invoice:
    st.subheader("Confirm PayPal action")
    data = st.session_state.pending_invoice

    if not data.get("client_email"):
        st.error("A customer email address is required before creating an invoice.")
        st.stop()

    col1, col2 = st.columns(2)

    if col1.button("✅ Confirm and Create Invoice", type="primary"):
        with st.spinner("Creating PayPal sandbox invoice..."):
            response = create_paypal_invoice(
                client_name=data.get("client_name"),
                amount=data.get("amount"),
                currency=data.get("currency") or "USD",
                description=data.get("description"),
                due_date=data.get("due_date"),
                client_email=data.get("client_email"),
            )

        log_activity(
            user_request=str(data),
            action="create_invoice",
            paypal_response=response,
        )

        if response.get("ok"):
            st.success("PayPal sandbox invoice created.")
            st.write(f"Invoice ID: `{response.get('invoice_id')}`")
            st.write(f"Status: `{response.get('status')}`")
            st.json(response)

            st.session_state.created_invoice_id = response.get("invoice_id")
            st.session_state.pending_invoice = None
        else:
            st.error(
                response.get("error", "PayPal invoice creation failed.")
            )

    if col2.button("❌ Cancel"):
        st.session_state.pending_invoice = None
        st.info("Cancelled. No PayPal action was taken.")
        st.rerun() 