import instructor
import openai
from pydantic import BaseModel

from Config import config


class SimpleModel(BaseModel):
    name: str

print("Initializing client with mode=Mode.JSON...")
client = instructor.from_openai(
    openai.OpenAI(
        base_url=config.BASE_URL if config.BASE_URL else "http://localhost:11434/v1",
        api_key=config.API_KEY if config.API_KEY else "ollama",
    ),
    mode=instructor.Mode.JSON
)

try:
    res = client.chat.completions.create(
        model=config.MODEL,
        messages=[{"role": "user", "content": "Give me a mock name. Respond only in JSON."}],
        response_model=SimpleModel,
    )
    print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
