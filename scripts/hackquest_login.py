"""
Discover HackQuest API auth endpoint and attempt login.
Intercepts network calls from the HackQuest login page to find the
correct endpoint, or tries known NestJS + Next.js API patterns.
"""
import json
import urllib.request
import urllib.error

BASE_CANDIDATES = [
    "https://api.hackquest.io",
    "https://www.hackquest.io/api",
    "https://hackquest.io/api",
]

AUTH_PATHS = [
    "/user/login",
    "/auth/login",
    "/auth/signin",
    "/users/signin",
    "/users/login",
    "/auth/email",
    "/auth/credentials",
    "/api/auth/callback/credentials",
]

HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.hackquest.io",
    "Referer": "https://www.hackquest.io/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ArbiSense/0.1",
}

BODY = json.dumps({
    "email": "steff.darwin@gmail.com",
    "password": "Icefoxz123159",
}).encode()

print("Probing HackQuest auth endpoints...\n")

for base in BASE_CANDIDATES:
    for path in AUTH_PATHS:
        url = base + path
        req = urllib.request.Request(url, data=BODY, headers=HEADERS, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                body = resp.read().decode()
                print(f"[200 OK] {url}")
                print(body[:500])
                print()
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code not in (404,):
                print(f"[HTTP {e.code}] {url} => {body[:200]}")
        except Exception as ex:
            pass  # connection refused, DNS, etc.

print("\nDone.")
