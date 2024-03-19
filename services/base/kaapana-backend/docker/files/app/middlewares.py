import html
import json
from fastapi import FastAPI, Request, Response
from starlette.types import Message, Receive, Scope, Send


def safe_html_escape(value):
    if isinstance(value, str):
        return html.escape(value)
    elif isinstance(value, list):
        return [safe_html_escape(i) for i in value]
    elif isinstance(value, dict):
        return {key: safe_html_escape(val) for key, val in value.items()}
    else:
        return value


class SanitizePostBody:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return

        async def sanitize_body():
            message = await receive()
            assert message["type"] == "http.request"

            body: bytes = message.get("body", b"")
            body: str = body.decode()
            data = json.loads(body)
            data = safe_html_escape(data)

            message["body"] = json.dumps(data).encode()
            return message

        await self.app(scope, sanitize_body, send)


class SanitizePutBody:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["method"] != "PUT":
            await self.app(scope, receive, send)
            return

        async def sanitize_body():
            message = await receive()
            assert message["type"] == "http.request"

            body: bytes = message.get("body", b"")
            body: str = body.decode()
            data = json.loads(body)
            data = safe_html_escape(data)

            message["body"] = json.dumps(data).encode()
            return message

        await self.app(scope, sanitize_body, send)


async def set_body(request: Request, body: bytes):
    async def receive() -> Message:
        return {"type": "http.request", "body": body}

    request._receive = receive


async def run_on_post_requests(request: Request):
    if request.method == "POST":
        print("=====================================")
        print("Running on POST Request")
        body = await request.json()

        body = safe_html_escape(body)
        # Convert the modified dictionary back to JSON
        modified_json = json.dumps(body)

        await set_body(request, body=modified_json.encode())

        body = await request.json()
        print(body)
        print("=====================================")

    return request


async def invoke_middlewares_on_requests(request: Request):
    request = await run_on_post_requests(request)
    return request


def invoke_middlewares_on_response(response: Response):
    return response
