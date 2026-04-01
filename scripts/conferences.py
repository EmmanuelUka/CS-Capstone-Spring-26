import requests
import json

API_KEY = "0q5yclRoF68+1bcVGqlIR8wsGbGXKPTz9AX+UfgYMkt1D4NyjaU67TD3gIsbEvFp"
URL = "https://api.collegefootballdata.com/conferences"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

response = requests.get(URL, headers=headers)

print("Status:", response.status_code)

if response.status_code != 200:
    print("Error:", response.text)
    exit()

data = response.json()

print(f"Total conferences: {len(data)}")

# Pretty print first few
for conf in data[:5]:
    print(conf)

# Save to JSON
with open("conferences.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Saved to conferences.json")