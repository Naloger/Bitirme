import os
import sys

# Ensure project root is in sys.path before importing local services
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from services.Agentic.HelperAgents.IntentAgent.IntentAgentHelpers import analyze

if __name__ == "__main__":
    print("Executing IntentAgent LangGraph...")
    result = analyze(
        x="Sistemdeki veritabanı yedeği alınamadı, disk kapasitesi %99 dolu! Acil destek gerekiyor!",
        k="Mesaj 'DB-Monitor-Bot' cron job'ından Slack üzerinden geldi. Sistem yöneticisi tatilde.",
    )
    print("\n--- Analysis Finished ---")
    for field, val in result.model_dump().items():
        print(f"{field}: {val}")
