"""
Guards the landing page's nginx.conf: the app page must be revalidated on every visit.

A browser that serves index.html from its cache never reaches oauth2-proxy, so after logout
or an expired session the app starts without a session instead of showing the login (#2494).
Runtime behaviour was checked by running the image with this config; this only guards the text.

Run from anywhere:
    pytest services/utils/base-landing-page/tests/test_nginx_conf.py
"""

import re
from pathlib import Path

NGINX_CONF = Path(__file__).resolve().parents[1] / "files/kaapana_app/nginx.conf"


def _location_block(conf: str, matcher: str) -> str:
    match = re.search(r"location\s+" + re.escape(matcher) + r"\s*\{([^}]*)\}", conf)
    assert match, f"nginx.conf has no 'location {matcher}' block"
    return match.group(1)


def test_app_page_is_revalidated_and_every_route_reaches_it():
    conf = NGINX_CONF.read_text()
    page = _location_block(conf, "= /index.html")
    assert 'add_header Cache-Control "no-cache";' in page
    # add_header in a location drops the ones of other blocks, so it is repeated here.
    assert 'add_header X-Frame-Options "SAMEORIGIN";' in page

    # "/" and app routes reach the block above only through nginx's internal redirect.
    root = _location_block(conf, "/")
    assert re.search(r"index\s+index\.html;", root)
    assert re.search(r"try_files\s+[^;]*\s/index\.html;", root)
