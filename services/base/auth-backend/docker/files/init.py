import logging

global error_page
error_page_path = "/kaapana/app/403.html"

logger = logging.getLogger("gunicorn.access")

def load_error_page():
    global error_page
    with open(error_page_path, "r", encoding="utf-8") as f:
        error_page = f.read()

load_error_page()
