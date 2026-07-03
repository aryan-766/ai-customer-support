import httpx
try:
    r = httpx.post("http://localhost:8000/api/v1/calls/start", json={"channel": "phone"})
    print("STATUS:", r.status_code)
    print("BODY:", r.text)
except Exception as e:
    print("Error:", e)
