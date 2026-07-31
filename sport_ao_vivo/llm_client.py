import os
from dotenv import load_dotenv

load_dotenv()

import config


class LLMUnavailable(Exception):
    pass


def _load_openrouter():
    try:
        from openai import OpenAI
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=config.OPENROUTER_API_KEY,
        )
    except Exception:
        return None


def is_available():
    return bool(config.OPENROUTER_API_KEY) and _load_openrouter() is not None


def status():
    if not config.OPENROUTER_API_KEY:
        return "OPENROUTER_API_KEY nao configurada"
    if _load_openrouter() is None:
        return "openai SDK nao instalado (pip install openai)"
    return f"pronto (openrouter/{config.LLM_MODEL})"


def generate(prompt, system=None, model=None, temperature=0.7, _retry=3):
    import time

    if not config.OPENROUTER_API_KEY:
        raise LLMUnavailable("OPENROUTER_API_KEY nao configurada")
    
    client = _load_openrouter()
    if client is None:
        raise LLMUnavailable("openai SDK nao instalado (pip install openai)")

    model = model or config.LLM_MODEL

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(_retry):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as err:
            err_str = str(err)
            if ("429" in err_str or "rate" in err_str.lower()) and attempt < _retry - 1:
                wait = 15 * (attempt + 1)
                print(f"     [rate limit] aguardando {wait}s antes de tentar novamente...")
                time.sleep(wait)
            else:
                raise
