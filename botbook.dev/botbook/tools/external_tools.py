import requests

def http_get(url: str):
    r = requests.get(url, timeout=10)
    return {
        "status": r.status_code,
        "data": r.text[:1000]
    }

def weather(city: str):
    r = requests.get(
        f"https://wttr.in/{city}?format=j1",
        timeout=10
    )
    return r.json()

def exchange_rate(base="USD"):
    r = requests.get(
        f"https://api.exchangerate.host/latest?base={base}",
        timeout=10
    )
    return r.json()
