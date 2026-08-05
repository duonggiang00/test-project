from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

print('Sending 6 requests to /auth/login...')
for i in range(6):
    response = client.post('/auth/login', data={'username': 'test@example.com', 'password': 'password'})
    print(f'Request {i+1}: Status {response.status_code}')
