import json
import sys

sys.stdin.read()
json.dump({"text": "x" * 100}, sys.stdout)
