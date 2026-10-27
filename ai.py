"""AI orqali taqdimot matnini yozish. Provayderni .env dagi AI_PROVIDER belgilaydi."""
import json
import re

import httpx

import config

LANG_NAMES = {"uz": "Uzbek (Latin script)", "ru": "Russian", "en": "English"}

PROMPT = """You are an expert presentation writer for students.
Create a presentation on the topic: "{topic}".
Language: {lang}. Number of slides in total: {n} (the first is the title slide, the last is a summary/conclusion).

Return ONLY valid JSON, no markdown, in exactly this shape:
{{
  "title": "presentation title",
  "subtitle": "short subtitle",
  "slides": [
    {{"title": "slide title", "bullets": ["point 1", "point 2", "point 3", "point 4"], "notes": "1-2 sentences the speaker can say"}}
  ]
}}

Rules:
- "slides" must contain exactly {m} content slides (title slide is generated separately).
- Each slide has 3-5 bullets, each bullet is a full, informative sentence of at most 22 words.
- Facts must be accurate. Do not invent statistics, names or dates.
- The last slide is the conclusion.
- Write everything in {lang}."""


class AIError(Exception):
    pass


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise AIError("AI javobida JSON topilmadi")
    return json.loads(text[start:end + 1])


async def _gemini(prompt: str) -> str:
    if not config.GEMINI_API_KEY:
        raise AIError("GEMINI_API_KEY kiritilmagan")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.5-flash:generateContent")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
    }
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(url, params={"key": config.GEMINI_API_KEY}, json=body)
    if r.status_code != 200:
        raise AIError(f"Gemini {r.status_code}: {r.text[:200]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _groq(prompt: str) -> str:
    if not config.GROQ_API_KEY:
        raise AIError("GROQ_API_KEY kiritilmagan")
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.7,
    }
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post("https://api.groq.com/openai/v1/chat/completions",
                         headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"}, json=body)
    if r.status_code != 200:
        raise AIError(f"Groq {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


async def _claude(prompt: str) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise AIError("ANTHROPIC_API_KEY kiritilmagan")
    body = {
        "model": "claude-sonnet-5-5",
        "max_tokens": 8000,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post("https://api.anthropic.com/v1/messages", json=body, headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        })
    if r.status_code != 200:
        raise AIError(f"Claude {r.status_code}: {r.text[:200]}")
    return "".join(b.get("text", "") for b in r.json()["content"])


PROVIDERS = {"gemini": _gemini, "groq": _groq, "claude": _claude}


async def generate_presentation(topic: str, n_slides: int, lang: str) -> dict:
    provider = PROVIDERS.get(config.AI_PROVIDER)
    if not provider:
        raise AIError(f"Noma'lum AI_PROVIDER: {config.AI_PROVIDER}")
    prompt = PROMPT.format(topic=topic, n=n_slides, m=n_slides - 1,
                           lang=LANG_NAMES.get(lang, "Uzbek (Latin script)"))
    last_err: Exception | None = None
    for _ in range(2):  # bitta qayta urinish
        try:
            data = _extract_json(await provider(prompt))
            slides = [s for s in data.get("slides", []) if s.get("title") and s.get("bullets")]
            if not slides:
                raise AIError("AI bo'sh slaydlar qaytardi")
            data["slides"] = slides
            return data
        except (AIError, json.JSONDecodeError, KeyError, httpx.HTTPError) as e:
            last_err = e
    raise AIError(str(last_err))
