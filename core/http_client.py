import httpx

_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        raise RuntimeError("HTTP Client is not initialized!")
    return _http_client