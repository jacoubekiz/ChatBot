# whatsapp_template_pdf.py
# Create a WhatsApp template with a PDF header and a single {{1}} variable in BODY,
# without requiring the caller to pass App ID explicitly.

import os
import mimetypes
import requests

GRAPH_VERSION = "v17.0"
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
    resp = requests.get(
        url,
        params=params or {},
        headers=headers or {},
        timeout=HTTP_TIMEOUT_GET,
    )
    _raise_for_api_error(resp)
    return resp.json()


def _http_post(url: str, params=None, headers=None, data=None, json_body=None):
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
    base = f"https://graph.facebook.com/{GRAPH_VERSION}/debug_token"

    # Attempt 1: self-introspection
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

    # Attempt 2: app token from env
    env_app_id = os.getenv("META_APP_ID")
    env_app_secret = os.getenv("META_APP_SECRET")
    if env_app_id and env_app_secret:
        app_token = f"{env_app_id}|{env_app_secret}"
        try:
            j2 = _http_get(base, params={
                "input_token": access_token,
                "access_token": app_token,
            })
            if "data" in j2 and "app_id" in j2["data"]:
                return j2["data"]["app_id"]
        except MetaApiError as e2:
            raise MetaApiError(
                "Could not resolve app_id from token. "
                f"Self-introspection error: {first_err or 'n/a'}; "
                f"App-token introspection error: {e2}"
            )

    raise MetaApiError(
        "Could not resolve app_id from token. "
        f"Self-introspection error: {first_err or 'n/a'}; "
        "No META_APP_ID/META_APP_SECRET set or second attempt failed."
    )


def create_whatsapp_template_with_pdf_auto_appid(
    access_token: str,
    waba_id: str,
    template_name: str,
    pdf_file_path: str,
    language: str = "en_US",
    category: str = "UTILITY",
    graph_version: str = GRAPH_VERSION,
) -> str:
    """
    1) Resolve app_id from access token
    2) Start resumable upload session: POST /{app_id}/uploads
    3) Upload bytes to session: POST /{upload_session_id}
    4) Create template on WABA: POST /{waba_id}/message_templates
    Returns the created template ID.
    """
    if not os.path.exists(pdf_file_path):
        raise FileNotFoundError(f"PDF file does not exist: {pdf_file_path}")

    file_name = os.path.basename(pdf_file_path)
    with open(pdf_file_path, "rb") as f:
        file_bytes = f.read()
    file_size = len(file_bytes)
    file_type = mimetypes.guess_type(pdf_file_path)[0] or "application/pdf"

    # 1) Resolve App ID
    app_id = resolve_app_id_from_token(access_token)

    # 2) Start resumable upload session
    init_url = f"https://graph.facebook.com/{graph_version}/{app_id}/uploads"
    init_params = {
        "file_name": file_name,
        "file_length": str(file_size),
        "file_type": file_type,
        "access_token": access_token,
    }
    init_resp = _http_post(init_url, params=init_params)
    init_json = init_resp.json()
    upload_session_id = init_json.get("id")
    if not upload_session_id:
        raise MetaApiError(f"Upload session init did not return id: {init_json}")

    # 3) Upload the bytes to the session to obtain the file handle
    upload_url = f"https://graph.facebook.com/{graph_version}/{upload_session_id}"
    upload_headers = {
        # For the upload step, Meta expects OAuth here (not Bearer)
        "Authorization": f"OAuth {access_token}",
        "file_offset": "0",
        # CHANGED: use octet-stream and remove 'Expect' header to avoid HTTP 417
        "Content-Type": "application/octet-stream",
        "Content-Length": str(file_size),  # requests sets this anyway; harmless to keep
    }
    upload_resp = _http_post(upload_url, headers=upload_headers, data=file_bytes)
    try:
        upload_json = upload_resp.json()
    except Exception:
        raise MetaApiError(f"Upload returned non-JSON (status {upload_resp.status_code}): {upload_resp.text}")

    file_handle = upload_json.get("h")
    if not file_handle:
        raise MetaApiError(f"Upload did not return a file handle: {upload_json}")

    # 4) Create the message template
    template_url = f"https://graph.facebook.com/{graph_version}/{waba_id}/message_templates"
    payload = {
        "name": template_name,
        "language": language,
        "category": category,
        "components": [
            {
                "type": "HEADER",
                "format": "DOCUMENT",
                "example": {"header_handle": [file_handle]},
            },
            {
                "type": "BODY",
                "text": "Dear  {{1}}, Please find the lesson plan attached.",
                "example": {"body_text": [["John"]]},
            },
        ],
    }
    template_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    tmpl_resp = _http_post(template_url, headers=template_headers, json_body=payload)
    tmpl_json = tmpl_resp.json()
    tmpl_id = tmpl_json.get("id")
    if not tmpl_id:
        raise MetaApiError(f"Template creation failed: {tmpl_json}")

    return tmpl_id


if __name__ == "__main__":
    ACCESS_TOKEN = "EAACWgHBBCVEBO7y3ZBHRrZBTQXgDbWxK7V4ZCenf5AbYvFjqyZCkj6fTERoeesFmnMumd0ZC3w8iZC7v00ORU3BIoTX9JA9EV61C4j5q10dFdZBN71oaezUIicCbWidggZCg0Bkof2Ent36Ng5QxZAAoTZBAQdhOAOZBKHmeMFINLhDf4WXKbzxC1vNJ0pG041VsGTr"
    WABA_ID = "190659524128108"
    TEMPLATE_NAME = "lesson_plan92025"
    PDF_PATH = "Adam_20_Session_Lesson_Plan.pdf"

    try:
        template_id = create_whatsapp_template_with_pdf_auto_appid(
            access_token=ACCESS_TOKEN,
            waba_id=WABA_ID,
            template_name=TEMPLATE_NAME,
            pdf_file_path=PDF_PATH,
            language="en_US",
            category="UTILITY",
            graph_version=GRAPH_VERSION,
        )
        print(f"Template created. ID: {template_id}")
    except Exception as e:
        print("Error:", e)
