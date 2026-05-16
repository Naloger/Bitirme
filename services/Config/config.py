import json
from typing import Optional
from pydantic import BaseModel, Field 



class APILLMConfig(BaseModel):
    provider: str = ""
    model: str = ""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 8000
    timeout: float = 60.0
    max_loops: int = 3


class AppConfig(BaseModel):
    api_config: APILLMConfig = Field(default_factory=APILLMConfig)

    @classmethod
    def from_json_file(cls, file_path: str) -> "AppConfig":
        try:
            with open(file_path, "r") as f:
                # Pydantic handles nested dictionary parsing automatically
                return cls.model_validate(json.load(f))
        except FileNotFoundError:
            print(f"! Config file {file_path} not found.")
            return cls()