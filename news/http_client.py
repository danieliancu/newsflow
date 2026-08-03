import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import requests
from django.conf import settings


class UnsafeURLError(ValueError):
    pass


class ResponseTooLargeError(ValueError):
    pass


def validate_public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Sunt permise numai URL-uri HTTP/HTTPS.")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URL-urile cu userinfo nu sunt permise.")
    if not parsed.hostname:
        raise UnsafeURLError("URL-ul nu conține un hostname valid.")
    hostname = parsed.hostname.rstrip(".").casefold()
    if hostname in {"localhost", "metadata.google.internal"} or hostname.endswith(".localhost"):
        raise UnsafeURLError("Destinațiile locale sau metadata cloud nu sunt permise.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Hostname-ul nu poate fi rezolvat: {hostname}.") from exc
    if not addresses:
        raise UnsafeURLError(f"Hostname-ul nu are adrese: {hostname}.")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or ip in ipaddress.ip_network("169.254.169.254/32"):
            raise UnsafeURLError(f"Adresa {address} nu este o destinație publică permisă.")
    return url


class SafeHTTPClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": settings.NEWSFLOW_USER_AGENT})

    def get(self, url, *, max_bytes, max_redirects=5):
        current = url
        for redirect_count in range(max_redirects + 1):
            validate_public_url(current)
            response = self.session.get(
                current,
                timeout=(settings.NEWSFLOW_CONNECT_TIMEOUT, settings.NEWSFLOW_READ_TIMEOUT),
                allow_redirects=False,
                stream=True,
            )
            if response.is_redirect or response.is_permanent_redirect:
                if redirect_count >= max_redirects:
                    response.close()
                    raise requests.TooManyRedirects(f"Prea multe redirectări pentru {url}.")
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise requests.RequestException("Redirect fără antet Location.")
                current = urljoin(current, location)
                continue
            response.raise_for_status()
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > max_bytes:
                response.close()
                raise ResponseTooLargeError(f"Răspunsul depășește limita de {max_bytes} bytes.")
            content = bytearray()
            for chunk in response.iter_content(chunk_size=65536):
                content.extend(chunk)
                if len(content) > max_bytes:
                    response.close()
                    raise ResponseTooLargeError(f"Răspunsul depășește limita de {max_bytes} bytes.")
            response._content = bytes(content)
            response._content_consumed = True
            response.url = current
            response.close()
            return response
        raise requests.TooManyRedirects(f"Prea multe redirectări pentru {url}.")
