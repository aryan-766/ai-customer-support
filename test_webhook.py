import requests

# Test the check_order_status tool
url = "http://localhost:8000/api/v1/eleven/webhook"

payload = {
    "tool_name": "check_order_status",
    "parameters": {
        "order_id": "AMB-12345"
    }
}

try:
    print(f"Sending webhook test to: {url}")
    print(f"Payload: {payload}")
    response = requests.post(url, json=payload)
    print("\nResponse Status Code:", response.status_code)
    print("Response Content:", response.json())
except Exception as e:
    print(f"Error connecting to webhook: {e}")
    print("Make sure your backend server is running on port 8000!")
