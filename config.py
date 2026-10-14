
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


def get_secret(key):
    value = os.getenv(key)

    if value:
        return value

    try:
        return st.secrets.get(key)
    except Exception:
        return None


OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is missing. Configure it in .env "
        "locally or Streamlit Secrets when deployed."
    )

LLM_MODEL = "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
