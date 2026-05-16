"""TaskAgent: Ollama + Pydantic version

Bu dosya orijinal OpenAI/instructor örneğini Ollama ile değiştirilmiş
ve Pydantic (pydantic v2 API) ile doğrulama yapan bir uygulamadır.

CTT_Task.py modellerini kullanarak kurumsal workflow'ları yapılandırır.

Kullanım:
- Localde Ollama çalışıyor olmalı (varsayılan: http://127.0.0.1:11434)
- Modelin JSON çıktı üretmesi için prompt'ta sıkı talimat veriyoruz
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import requests

from CTT_Task import TaskTree


def call_ollama(prompt_text: str, model: str = "gemma4:e2b") -> str:
    """Try calling local Ollama HTTP API, fall back to the ollama CLI if HTTP is not available.

    Returns the raw text output from the model.
    """
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt_text,
        # small batch and single completion to keep response simple
        "n": 1,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        # Ollama may stream or return a JSON envelope. Try to extract text safely.
        try:
            body = resp.json()
            # Search for a plausible text field in the response
            if isinstance(body, dict):
                # common key used by Ollama API might be 'text' or 'content'; adapt if needed
                for key in ("text", "content", "output", "response"):
                    if key in body:
                        return body[key]
                # sometimes the response is an object with 'choices'
                if "choices" in body and isinstance(body["choices"], list) and body["choices"]:
                    ch = body["choices"][0]
                    if isinstance(ch, dict) and "text" in ch:
                        return ch["text"]
            # fallback to raw text
            return resp.text
        except ValueError as json_error:
            # not json, return raw text
            sys.stderr.write(f"Warning: Could not parse JSON response: {json_error}\n")
            return resp.text
    except (requests.RequestException, requests.Timeout) as http_error:
        # Fallback to CLI invocation. Different versions of the ollama CLI accept the
        # prompt in different ways, so try a couple of fallbacks:
        # 1) Try the `--prompt` flag (newer CLI) - keep this attempt for compatibility.
        # 2) If that fails (unknown flag), try sending the prompt via stdin to `ollama run <model>`.
        # Normalize model id: some callers use 'ollama/<id>' while the local CLI expects '<id>'
        if isinstance(model, str) and model.startswith("ollama/"):
            model = model.split("/", 1)[1]

        try:
            # First attempt: explicit --prompt flag
            proc = subprocess.run(
                ["ollama", "run", model, "--prompt", prompt_text],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except FileNotFoundError as cli_error:
            raise RuntimeError(
                "Cannot contact Ollama API and ollama CLI not found. Start Ollama or install the ollama CLI."
            ) from cli_error

        # If the first CLI call succeeded, return output
        if proc.returncode == 0:
            return proc.stdout

        # If the CLI returned a non-zero code, try the stdin fallback which is supported
        # by some ollama CLI versions (they read the prompt from stdin when no --prompt flag).
        try:
            proc2 = subprocess.run(
                ["ollama", "run", model],
                input=prompt_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except FileNotFoundError as cli_error:
            # This should be rare because we already attempted a run above, but handle defensively
            raise RuntimeError(
                "Cannot contact Ollama API and ollama CLI not found. Start Ollama or install the ollama CLI."
            ) from cli_error

        if proc2.returncode == 0:
            return proc2.stdout

        # Neither CLI approach worked; raise a helpful error including both stderr outputs.
        raise RuntimeError(
            f"ollama CLI failed. attempt1_stderr={proc.stderr!r} attempt2_stderr={proc2.stderr!r}"
        ) from http_error


def build_prompt(user_text: str) -> str:
    # Açıkça sadece JSON dönmesini ve beklenen alanları kullanmasını söyle
    schema_example = {
        "root_tasks": [
            {
                "id": "EXP-APR-001",
                "title": "Seyahat harcaması gönderme",
                "description": "Çalışan tarafından harcama formunun doldurulması ve sisteme gönderilmesi",
                "status": "not_started",
                "priority": "critical",
                "assignee": "employee",
                "due_date": "2026-05-20",
                "dependencies": [],
                "children": [
                    {
                        "id": "EXP-APR-002",
                        "title": "Yöneticinin onaylaması",
                        "description": "Doğrudan yönetici tarafından giderin incelenmesi ve onaylanması",
                        "status": "not_started",
                        "priority": "critical",
                        "assignee": "manager",
                        "due_date": "2026-05-25",
                        "dependencies": ["EXP-APR-001"],
                        "children": [
                            {
                                "id": "EXP-APR-003",
                                "title": "Mali kontrol",
                                "description": "Muhasebe departmanı tarafından kontrol ve doğrulama",
                                "status": "not_started",
                                "priority": "critical",
                                "assignee": "accounting",
                                "due_date": "2026-06-01",
                                "dependencies": ["EXP-APR-002"],
                                "children": [
                                    {
                                        "id": "EXP-APR-004",
                                        "title": "Ödeme gerçekleştirme",
                                        "description": "Mali departman tarafından çalışana ödemenin yapılması",
                                        "status": "not_started",
                                        "priority": "critical",
                                        "assignee": "finance",
                                        "due_date": "2026-06-15",
                                        "dependencies": ["EXP-APR-003"],
                                        "children": []
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ],
        "metadata": {
            "workflow_id": "EXPENSE_APPROVAL_v1",
            "department": "Finance",
            "created_at": "2026-05-15"
        }
    }

    prompt = (
        "You are an enterprise workflow structuring expert.\n"
        "Produce ONLY valid JSON that exactly matches the schema described below. "
        "Do not add any explanation or markdown, return raw JSON only.\n"
        "Use these enum values:\n"
        "  - status: 'not_started', 'in_progress', 'completed', 'blocked', 'cancelled'\n"
        "  - priority: 'low', 'medium', 'high', 'critical'\n"
        "Date format: YYYY-MM-DD\n\n"
        "Schema (example):\n"
        f"{json.dumps(schema_example, ensure_ascii=False, indent=2)}\n\n"
        "User input: "
        f"{user_text}\n"
    )
    return prompt


if __name__ == "__main__":
    user_content = (
        "Seyahat onayı süreci: Çalışan harcamayı girer -> Yönetici onaylar -> "
        "Muhasebe kontrol eder -> Ödeme gerçekleştirilir. Kritik öncelik, 2026-06-15 son tarih."
    )

    workflow_prompt = build_prompt(user_content)

    try:
        raw_response = call_ollama(workflow_prompt, model="ollama/gemma4:e2b")
    except RuntimeError as runtime_error:
        print("Ollama çağrısı başarısız:", str(runtime_error), file=sys.stderr)
        raise

    # Bazı modeller ek boşluk veya açıklama bırakabilir; JSON parsellemeyi güvenli yapmak için
    raw_str = raw_response.strip()

    # Eğer çıktı içinde tek bir JSON nesnesi varsa bunu ayıkla
    try:
        # Bazı modeller JSON'u bir tırnak içinde dönebilir; bu durumda strip '```' veya açıklamaları
        # temizlemek gerekebilir. Ayrıca bazı modeller terminal kaçış/ANSI kodları
        # veya diğer kontrol karakterlerini çıktıya ekleyebilir; bunları temizleyelim.
        # Remove common ANSI escape sequences (e.g. "\x1b[1D", "\x1b[K").
        raw_str = re.sub(r"\x1b\[[0-9;?]*[ -/]*[@-~]", "", raw_str)

        # Basit temizleme: bazı modeller 'Thinking...' gibi metinler ekleyebilir;
        # JSON bloğunu almak için ilk '{' ile son '}' arasını alıyoruz.
        start = raw_str.find("{")
        end = raw_str.rfind("}")
        if start != -1 and end != -1:
            json_text = raw_str[start:end+1]
        else:
            json_text = raw_str

        # Sanitize JSON-like output: some models print pretty JSON but include
        # literal newline characters inside quoted strings (invalid JSON).
        # We convert unescaped control characters inside JSON strings into
        # the corresponding escape sequences so the result can be parsed.
        def _sanitize_json_like(s: str) -> str:
            out_chars = []
            in_string = False
            escape = False
            for ch in s:
                if in_string:
                    if escape:
                        # previous backslash escapes this char; keep both
                        out_chars.append(ch)
                        escape = False
                        continue
                    if ch == "\\":
                        out_chars.append(ch)
                        escape = True
                        continue
                    if ch == '"':
                        out_chars.append(ch)
                        in_string = False
                        continue
                    # If we encounter an unescaped control character, escape it
                    if ch == "\n":
                        out_chars.append("\\n")
                        continue
                    if ch == "\r":
                        out_chars.append("\\r")
                        continue
                    # Replace other control chars (0x00-0x1f) with \u00XX
                    if ord(ch) < 0x20:
                        out_chars.append(f"\\u{ord(ch):04x}")
                        continue
                    out_chars.append(ch)
                else:
                    out_chars.append(ch)
                    if ch == '"':
                        in_string = True
                        escape = False
            return ''.join(out_chars)

        sanitized = _sanitize_json_like(json_text)
        try:
            parsed = json.loads(sanitized)
        except json.JSONDecodeError:
            # If sanitization still fails, print the sanitized text for debugging
            print("Model ıktısı JSON olarak parse edilemedi:\n", raw_str, file=sys.stderr)
            raise
    except json.JSONDecodeError as json_error:
        print("Model çıktısı JSON olarak parse edilemedi:\n", raw_str, file=sys.stderr)
        raise json_error

    # Pydantic ile doğrula
    tree = TaskTree.model_validate(parsed)
    print(tree.model_dump_json(indent=2, ensure_ascii=False))

