import json
def beauty_json(data: dict) -> str:
    return json.dumps(data, indent=4, ensure_ascii=False)


def list_to_str(data: list) -> str:
    """
    Chuyển một list thành chuỗi, mỗi phần tử cách nhau bằng dấu phẩy và khoảng trắng \n
    VD: [1.2, 3.4, 5.6] -> "1.2, 3.4, 5.6"
    """
    return ", ".join(str(item) for item in data)