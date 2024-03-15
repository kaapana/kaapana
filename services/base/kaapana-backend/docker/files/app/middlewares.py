import html
import json
from fastapi import FastAPI, Request, Response


def safe_html_escape(value):
    if isinstance(value, str):
        return html.escape(value)
    elif isinstance(value, list):
        return [safe_html_escape(i) for i in value]
    elif isinstance(value, dict):
        return {key: safe_html_escape(val) for key, val in value.items()}
    else:
        return value


# async def set_body(request: Request, body: bytes):
#      async def receive() -> Message:
#          return {"type": "http.request", "body": body}
#      request._receive = receive


async def run_on_post_requests(request: Request):
    if request.method == "POST":
        print("=====================================")
        print("Running on POST Request")
        body = await request.json()
        print(body)

        body = safe_html_escape(body)
        # Convert the modified dictionary back to JSON
        modified_json = json.dumps(body)

        request._body = modified_json.encode()  # Convert the JSON string back to bytes

        # body = await request.json()
        print(request._body)
        print("=====================================")
    return request


async def invoke_middlewares_on_requests(request: Request):
    request = await run_on_post_requests(request)
    return request


def invoke_middlewares_on_response(response: Response):
    return response
