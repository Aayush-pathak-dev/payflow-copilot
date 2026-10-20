import streamlit as st

st.set_page_config(
    page_title="PayFlow Copilot",
    page_icon="💸",
    layout="centered",
)

st.title("💸 PayFlow Copilot")
st.caption("Turn plain English into PayPal invoice actions.")

st.warning("PayPal Sandbox — no real money is moved.", icon="⚠️")

user_input = st.chat_input(
    "Try: Create a $250 invoice for Rahul for 10 hours of web design, due in 7 days"
)

if user_input:
    st.write("You said:")
    st.info(user_input)