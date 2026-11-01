"""Start the API with configured host and port; LAN exposure must be explicit."""

from __future__ import annotations

import ipaddress

import uvicorn

from k9_expert.application.composition import ApplicationSettings, compose, load_settings
from k9_expert.presentation.api import create_app


def check_exposure(settings: ApplicationSettings) -> None:
    """Refuse a non-loopback bind unless allow_lan is set and admin mutations are protected."""
    try:
        loopback = ipaddress.ip_address(settings.host).is_loopback
    except ValueError:
        loopback = settings.host == "localhost"
    if loopback:
        return
    if not settings.allow_lan:
        raise SystemExit(f"Refusing to bind {settings.host}: set [server] allow_lan = true.")
    if not settings.admin_secret:
        raise SystemExit("LAN exposure requires K9_ADMIN_SECRET to protect administration.")


def main() -> None:
    settings = load_settings()
    check_exposure(settings)
    uvicorn.run(create_app(compose(settings)), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
