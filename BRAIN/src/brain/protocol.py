import json
from typing import Any, Dict

def dumps(msg: Dict[str, Any]) -> str:
    return json.dumps(msg, ensure_ascii=False)

def loads(raw: str) -> Dict[str, Any]:
    return json.loads(raw)