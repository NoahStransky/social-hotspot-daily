import urllib.request
import json

# Check what's at hotspot.edgesoft.org (the old domain)
try:
    req = urllib.request.Request(
        "https://hotspot.edgesoft.org/api/subscribe",
        data=json.dumps({"email": "test@test.com", "turnstile_token": "test"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    r = urllib.request.urlopen(req, timeout=5)
    print("hotspot.edgesoft.org/api/subscribe:", r.status, r.read().decode()[:200])
except urllib.error.HTTPError as e:
    print("hotspot.edgesoft.org/api/subscribe HTTP", e.code, e.read().decode()[:200])
except Exception as e:
    print("hotspot.edgesoft.org/api/subscribe error:", e)

# Check Vercel
try:
    req2 = urllib.request.Request(
        "https://social-hotspot-daily.vercel.app/api/subscribe",
        data=json.dumps({"email": "test@test.com"}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    r2 = urllib.request.urlopen(req2, timeout=5)
    print("Vercel /api/subscribe:", r2.status, r2.read().decode()[:200])
except urllib.error.HTTPError as e:
    print("Vercel /api/subscribe HTTP", e.code, e.read().decode()[:200])
except Exception as e:
    print("Vercel /api/subscribe error:", e)
