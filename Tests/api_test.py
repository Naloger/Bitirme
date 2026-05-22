from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient

from backend.api.api import app


def main() -> None:
    client = TestClient(app)
    client.post("/api/unstructured-pages",
                                  json={"raw_text": "Smoke test" ,
                                        "predicted_output":"empty pred out",
                                        "prediction_error":"1" })





if __name__ == "__main__":
    main()
