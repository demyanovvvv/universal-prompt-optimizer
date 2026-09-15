import json
import sys

payload = json.load(sys.stdin)
json.dump({"received": payload}, sys.stdout)
