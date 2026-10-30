"""Fetch customer-supplied URLs safely (blocks SSRF: no private/internal addresses, size + time limits,
redirects re-validated, connects to the vetted IP so DNS tricks can't swap the target)."""
import http.client
import ipaddress
import socket
import ssl
import time
import urllib.parse
from typing import Dict

MAX_BYTES = 1_500_000
UA = "SterlingVanceAuditBot/1.0 (website audit requested by the site owner)"


class FetchError(Exception):
    pass


def _vet_host(host: str, allow_private: bool) -> str:
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise FetchError("We couldn't find that website address.")
    ip = infos[0][4][0]
    addr = ipaddress.ip_address(ip)
    if not allow_private and (addr.is_private or addr.is_loopback or addr.is_link_local
                              or addr.is_reserved or addr.is_multicast or addr.is_unspecified):
        raise FetchError("That address is not a public website.")
    return ip


class _HTTP(http.client.HTTPConnection):
    def __init__(self, host, port, ip, timeout):
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _HTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, ip, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw or len(raw) > 300:
        raise FetchError("Please enter your website address.")
    if "://" not in raw:
        raw = "https://" + raw
    p = urllib.parse.urlsplit(raw)
    if p.scheme not in ("http", "https") or not p.hostname or "." not in p.hostname:
        raise FetchError("Please enter a valid website address, like example.com")
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))


def fetch(url: str, timeout: float = 8.0, max_redirects: int = 4, allow_private: bool = False) -> Dict:
    url = normalize_url(url)
    start = time.time()
    for _ in range(max_redirects + 1):
        p = urllib.parse.urlsplit(url)
        port = p.port or (443 if p.scheme == "https" else 80)
        ip = _vet_host(p.hostname, allow_private)
        conn = (_HTTPS if p.scheme == "https" else _HTTP)(p.hostname, port, ip, timeout)
        try:
            path = (p.path or "/") + (("?" + p.query) if p.query else "")
            conn.request("GET", path, headers={"Host": p.netloc, "User-Agent": UA,
                                               "Accept": "text/html,text/plain,*/*;q=0.5",
                                               "Accept-Encoding": "identity"})
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308) and resp.getheader("Location"):
                url = urllib.parse.urljoin(url, resp.getheader("Location"))
                if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
                    raise FetchError("The site redirected somewhere we can't open.")
                continue
            body = resp.read(MAX_BYTES + 1)
            truncated = len(body) > MAX_BYTES
            return {"status": resp.status, "final_url": url, "headers": {k.lower(): v for k, v in resp.getheaders()},
                    "text": body[:MAX_BYTES].decode(resp.headers.get_content_charset() or "utf-8", errors="replace"),
                    "bytes": min(len(body), MAX_BYTES), "truncated": truncated, "seconds": time.time() - start}
        except (socket.timeout, TimeoutError):
            raise FetchError("The website took too long to respond.")
        except (OSError, http.client.HTTPException, ssl.SSLError) as e:
            raise FetchError("We couldn't open that website (%s)." % type(e).__name__)
        finally:
            conn.close()
    raise FetchError("The website redirected too many times.")
