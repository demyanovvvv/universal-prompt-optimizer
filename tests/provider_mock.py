import json
import sys


payload = json.load(sys.stdin.buffer)
response = {"text": " ".join(payload.get("expect", [])) or "mock provider response"}
sys.stdout.buffer.write(
    json.dumps(
        {"response": response, "metrics": {"inputTokens": 1, "outputTokens": 1, "cost": 0.0}},
        ensure_ascii=False,
    ).encode("utf-8")
)
