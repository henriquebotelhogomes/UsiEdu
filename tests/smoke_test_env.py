"""Teste rápido do fluxo completo com chaves do .env."""

import http.client
import json

conn = http.client.HTTPConnection("localhost", 8002)
headers = {"Content-Type": "application/json"}

# 1. Login JWT com secret real
conn.request(
    "POST",
    "/auth/login",
    json.dumps({"email": "ana@demo.usiedu", "password": "estudante123"}),
    headers,
)
resp = conn.getresponse()
body = json.loads(resp.read())
print(f"1. Login: {resp.status} | perfil: {body['profile']}")
print(f"   Token: {body['access_token'][:30]}...")
token = body["access_token"]

# 2. Chat com LLM real (DeepSeek V4 Flash)
chat_headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}",
}
conn.request(
    "POST",
    "/chat",
    json.dumps({"session_id": "teste-env-1", "message": "Quero ver minhas notas"}),
    chat_headers,
)
resp2 = conn.getresponse()
chat = json.loads(resp2.read())
print(f"2. Chat: {resp2.status} | intent: {chat['intent']} | agentes: {chat['agents_involved']}")
print(f"   Resposta: {chat['answer'][:150]}")
