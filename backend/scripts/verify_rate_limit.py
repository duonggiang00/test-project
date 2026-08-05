from fastapi.testclient import TestClient
import sys
import os

# Ensure the backend directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app

def run_test():
    client = TestClient(app)
    
    print("Testing Rate Limit: Sending 6 requests to /auth/login...")
    for i in range(1, 7):
        response = client.post("/auth/login", data={"username": "test@example.com", "password": "password"})
        print(f"Request {i}: Status {response.status_code}")
        
        # The 6th request MUST be 429
        if i == 6:
            if response.status_code != 429:
                raise AssertionError(f"Rate Limit Failed! Expected 429, got {response.status_code}. Fake reporting detected!")
            else:
                print("\n[SUCCESS] Rate Limit Tightly Confirmed! (HTTP 429 received on the 6th request)")

if __name__ == "__main__":
    run_test()
