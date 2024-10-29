import os
from openai import OpenAI
import helpers
OPENAI_API_KEY = helpers.config("OPENAI_API_KEY", default = None)


def get_openai_client():
    return  OpenAI(
    # Defaults to os.environ.get("OPENAI_API_KEY")
    api_key= OPENAI_API_KEY,
)



def chat_with_openai(message, model="gpt-4o-mini", raw=False):
    client = get_openai_client()
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are an amazing code assistant",
            },
            {
                "role": "user",
                "content": message,
            }
        ],
        model=model,
    )
    if raw:
        return response
    return response.choices[0].message.content