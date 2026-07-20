import requests
# Yaha apni details bharein
ZOHO_CLIENT_ID="1000.O6YUV77LOA9PW9KY4VX6YF0OXAZ4LY"
ZOHO_CLIENT_SECRET="d2b61526c177813ce4501d4d06c4370d3f72b30ff4"
GRANT_CODE= "1000.97fbb278eff2567d3077a38ec5fa79e4.4c8c3af7e0ec64ee69afe2e19134b78e"
# Agar aapka account .com par hai toh zoho.com use karein
ZOHO_DOMAIN = "accounts.zoho.in" 
url = f"https://{ZOHO_DOMAIN}/oauth/v2/token"
payload = {
    'grant_type': 'authorization_code',
    'client_id': ZOHO_CLIENT_ID,
    'client_secret': ZOHO_CLIENT_SECRET,
    'code': GRANT_CODE,
    'redirect_uri': "https://api-console.zoho.in/client/1000.D56YH25JHNEDUWJEIQN6XX264SW1QT" # Yaha apna exact wahi redirect URL dalein jo aapne Zoho me Client banate waqt dala tha
}
response = requests.post(url, data=payload)
print(response.json())