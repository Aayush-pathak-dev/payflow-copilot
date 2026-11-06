import os
from importlib.metadata import version
from dotenv import load_dotenv
from paypal_agent_toolkit.openai.toolkit import PayPalToolkit
from paypal_agent_toolkit.shared.configuration import Configuration, Context

load_dotenv()  # read .env into environment variables

print("Toolkit version:", version("paypal-agent-toolkit"))

config = Configuration(
    actions={"invoices": {"create": True, "get": True}},  # which tool groups to turn on
    context=Context(sandbox=True),                        # sandbox only
)
toolkit = PayPalToolkit(
    os.getenv("PAYPAL_CLIENT_ID"), os.getenv("PAYPAL_CLIENT_SECRET"), config
)

# Every tool name plus the arguments it expects
for t in toolkit.get_openai_chat_tools():
    fn = t["function"]
    print("\nTOOL:", fn["name"])
    print("ARGS:", fn["parameters"])

# Methods on the low-level API object (look for run / create_invoice)
api = toolkit.get_paypal_api()
print("\nAPI methods:", [m for m in dir(api) if not m.startswith("_")])