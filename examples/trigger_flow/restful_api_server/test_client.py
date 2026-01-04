import httpx

response = httpx.post(
    "http://127.0.0.1:15365/test",
    json={
        "int_number": 1234,
    },
    timeout=300,
)
if response.status_code == 200:
    print(response.json())
