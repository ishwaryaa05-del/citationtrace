import os
from langsmith import Client


def get_langsmith_client():
    api_key = os.getenv("LANGSMITH_API_KEY")
    if api_key:
        return Client(api_key=api_key)
    return None


LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "citationtrace")
