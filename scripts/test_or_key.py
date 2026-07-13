import urllib.request, json, os
key = os.environ.get('OPENROUTER_API_KEY','')
req = urllib.request.Request('https://openrouter.ai/api/v1/models', headers={'Authorization': f'Bearer {key}'})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    print(f'OpenRouter OK: {len(data.get("data",[]))} models available')
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.read().decode()[:200]}')
