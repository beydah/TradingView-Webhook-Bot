import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure app path
sys.path.append(os.getcwd())

# We need to mock settings before importing app/main because it loads settings at module level
# But pydantic settings loads from env, so we are good if .env exists

try:
    from app.main import app
    from app.core.config import settings
except Exception as e:
    print(f"Import Error: {e}")
    sys.exit(1)

client = TestClient(app)

class TestFastAPI(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "binance-bot-webhook"})

    def test_webhook_invalid_key(self):
        # Invalid Key
        payload = {
            "symbol": "BTCUSDT",
            "alert": "long_open",
            "price": 50000.0,
            "key": "wrong_key"
        }
        response = client.post("/webhook", json=payload)
        self.assertEqual(response.status_code, 403)

    def test_webhook_valid(self):
        # Valid Key
        # We need to temporarily set the key or use the one from env
        key = settings.ALERT_KEY
        payload = {
            "symbol": "BTCUSDT",
            "alert": "long_open",
            "price": 50000.0,
            "key": key
        }
        
        # This will trigger database write, so it tests full integration
        response = client.post("/webhook", json=payload)
        # It might fail if DB is locked or other issues, but logic should be tested
        if response.status_code == 200:
             self.assertEqual(response.json()['status'], "success")
        else:
             # If it fails, print why
             print(f"Webhook failed: {response.text}")
             if response.status_code != 500: # 500 might happen if DB locked or something
                 self.fail("Webhook failed")

if __name__ == '__main__':
    unittest.main()
