import html
import json
from fastapi import FastAPI, Request, Response
from starlette.types import Message, Receive, Scope, Send
from starlette.datastructures import QueryParams
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import urlencode


def safe_html_escape(value):
    """
    Recursively escape HTML characters in a string, list, or dictionary.

    Args:
        value (str, list, tuple, dict): The input value to escape.

    Returns:
        str, list, tuple, dict: The escaped value.
    """
    if isinstance(value, str):
        # If the value is a string, escape HTML characters
        return html.escape(value)
    elif isinstance(value, list):
        # If the value is a list, recursively call safe_html_escape on each element
        return [safe_html_escape(i) for i in value]
    elif isinstance(value, tuple):
        # If the value is a tuple, recursively call safe_html_escape on each element
        # store in a list, then revert it back to tuple and return
        out = [safe_html_escape(i) for i in value]
        return tuple(out)
    elif isinstance(value, dict):
        # If the value is a dictionary, recursively call safe_html_escape on each value
        return {key: safe_html_escape(val) for key, val in value.items()}
    else:
        # If the value is not a string, list, or dictionary, return it unchanged
        return value


def sanitize_inputs(*inputs):
    """
    Function to sanitize input values through different processing e.g. html escaping.

    Args:
    *inputs: Variable number of input values to be sanitized.

    Returns:
    Either a single sanitized input value if only one input is provided,
    or a tuple of sanitized input values if multiple inputs are provided.
    """
    # Initialize an empty list to store processed input values
    processed = []
    for value in inputs:
        # Sanitize the input value by escaping HTML special characters
        value = safe_html_escape(value)
        processed.append(value)

    # Check if only one input value was provided
    # Return the single sanitized input value
    if len(processed) == 1:
        return processed[0]

    # Return a tuple of sanitized input values if multiple inputs were provided
    return tuple(processed)


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
            if not body:
                return message

            # catch the error if it
            # fails to decode and load the body to json
            try:
                body: str = body.decode()
                # Deserialize the JSON body into a Python dictionary
                data = json.loads(body)
            except ValueError:
                return message

            # Sanitize the data (e.g., escape HTML)
            data = sanitize_inputs(data)
            message["body"] = json.dumps(data).encode()

            return message

        # Pass the modified scope to the next middleware or application
        await self.app(scope, sanitize_body, send)


class SanitizeQueryParams(BaseHTTPMiddleware):
    """
    Middleware to sanitize query parameters in incoming requests.

    This middleware intercepts incoming HTTP requests, checks for query parameters,
    and sanitizes the values to prevent potential security risks like XSS (Cross-Site Scripting).
    """

    async def dispatch(self, request: Request, call_next):
        """
        Intercepts the request, sanitizes the query parameters, and forwards the request.

        Args:
            request (Request): The incoming HTTP request object.
            call_next (Callable): A function to call the next middleware or handler.

        Returns:
            Response: The HTTP response from the next middleware or handler.
        """
        # Access query parameters
        query_params = request.query_params

        if query_params:
            # update the query param values with sanitized values
            modified_dict = sanitize_inputs(query_params._dict)
            # Reconstruct QueryParams object with modified dictionary
            modified_query_params = QueryParams(modified_dict)

            # Update request with modified query parameters
            request._query_params = modified_query_params

            scope_query: bytes = request.scope.get("query_string", b"")
            # also replace the query from scope if exists
            if scope_query:
                request.scope["query_string"] = urlencode(modified_dict).encode("utf-8")

        # Call the next middleware or the handler
        response = await call_next(request)
        return response
