import html
import json
from fastapi import FastAPI, Request, Response
from starlette.types import Message, Receive, Scope, Send
from starlette.datastructures import QueryParams
from starlette.middleware.base import BaseHTTPMiddleware


def safe_html_escape(value):
    """
    Recursively escape HTML characters in a string, list, or dictionary.

    Args:
        value (str, list, dict): The input value to escape.

    Returns:
        str, list, dict: The escaped value.
    """
    if isinstance(value, str):
        # If the value is a string, escape HTML characters
        return html.escape(value)
    elif isinstance(value, list):
        # If the value is a list, recursively call safe_html_escape on each element
        return [safe_html_escape(i) for i in value]
    elif isinstance(value, dict):
        # If the value is a dictionary, recursively call safe_html_escape on each value
        return {key: safe_html_escape(val) for key, val in value.items()}
    else:
        # If the value is not a string, list, or dictionary, return it unchanged
        return value


class SanitizeBodyInputs:
    """
    This middleware is designed to intercept PUT and POST requests, sanitize their request bodies
    (e.g., escaping HTML characters), and then pass the modified request body along to the
    FastAPI application
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        Middleware entry point.

        Args:
            scope (Scope): The ASGI scope.
            receive (Receive): Callable to receive messages.
            send (Send): Callable to send messages.

        Returns:
            None
        """

        # Check if the incoming request is an HTTP request and if it's a PUT or POST request
        if scope["type"] != "http" or not (
            scope["method"] == "PUT" or scope["method"] == "POST"
        ):
            # Pass the scope to the next middleware or application
            await self.app(scope, receive, send)
            return

        async def sanitize_body():
            """
            Sanitize the request body.
            """
            # Receive the incoming message
            message = await receive()
            assert message["type"] == "http.request"

            # Extract the body from the message and decode it
            body: bytes = message.get("body", b"")
            body: str = body.decode()
            # Deserialize the JSON body into a Python dictionary
            data = json.loads(body)
            # Sanitize the data (e.g., escape HTML)
            data = safe_html_escape(data)

            message["body"] = json.dumps(data).encode()
            return message

        # Pass the modified scope to the next middleware or application
        await self.app(scope, sanitize_body, send)


class SanitizeQueryParams(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Access query parameters
        query_params = request.query_params

        if query_params:
            # update the query param values with html escaped values
            modified_dict = safe_html_escape(query_params._dict)
            # Reconstruct QueryParams object with modified dictionary
            modified_query_params = QueryParams(modified_dict)

            # Update request with modified query parameters
            request._query_params = modified_query_params

        # Call the next middleware or the handler
        response = await call_next(request)
        return response
