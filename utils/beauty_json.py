import json
def beauty_json(data: dict) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)