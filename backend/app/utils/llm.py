from openai import OpenAI
import logging
from app.core.config import settings

def process_llm_request_openai(model, messages, response_schema):
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_schema,
            max_tokens=4096,
        )
        return response.choices[0].message.parsed
    except Exception as e:
        logging.error(e)
        return str(e)
