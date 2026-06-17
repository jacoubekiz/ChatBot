import requests


HTTP_TIMEOUT_GET = 60
HTTP_TIMEOUT_POST = 120


class MetaApiError(Exception):
    pass


def _raise_for_api_error(resp: requests.Response):
    """Raise MetaApiError with body if status != 200."""
    if resp.status_code == 200:
        return
    try:
        body = resp.json()
    except Exception:
        body = resp.text
    raise MetaApiError(f"HTTP {resp.status_code}: {body}")


def _http_get(url: str, params=None, headers=None):
    """Perform HTTP GET request with error handling."""
    resp = requests.get(
        url,
        params=params or {},
        headers=headers or {},
        timeout=HTTP_TIMEOUT_GET,
    )
    _raise_for_api_error(resp)
    return resp.json()


def _http_post(url: str, params=None, headers=None, data=None, json_body=None):
    """Perform HTTP POST request with error handling."""
    resp = requests.post(
        url,
        params=params or {},
        headers=headers or {},
        data=data,
        json=json_body,
        timeout=HTTP_TIMEOUT_POST,
    )
    _raise_for_api_error(resp)
    return resp


def resolve_app_id_from_token(access_token: str) -> str:
    """
    Resolve app_id from the access token using /debug_token.
    Falls back to APP_TOKEN formed from META_APP_ID|META_APP_SECRET if needed.
    """
    base = f"https://graph.facebook.com/v22.0/debug_token"
    try:
        j = _http_get(base, params={
            "input_token": access_token,
            "access_token": access_token,
        })
        if "data" in j and "app_id" in j["data"]:
            return j["data"]["app_id"]
    except MetaApiError as e1:
        first_err = str(e1)
    else:
        first_err = None

    raise MetaApiError(
        "Could not resolve app_id from token. "
        f"Self-introspection error: {first_err or 'n/a'}; "
        "No META_APP_ID/META_APP_SECRET set or second attempt failed."
    )
