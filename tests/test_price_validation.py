import asyncio
import os
import unittest
from unittest.mock import patch

# Use dummy credentials and mock queueing so tests never contact an exchange.
for name in ("BINANCE_API_KEY", "BINANCE_SECRET_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_USER_ID", "ALERT_KEY"):
    os.environ[name] = "test-only"

from fastapi import HTTPException
from app.api.webhook import WebhookPayload, webhook


class PriceValidationTest(unittest.TestCase):
    def test_non_finite_and_non_positive_prices_never_reach_queue(self):
        for value in ("NaN", "Infinity", "-Infinity", 0, -1):
            with self.subTest(value=value), patch("app.api.webhook.tradingview_service.add_to_queue") as queue:
                payload = WebhookPayload(symbol="BTCUSDT", alert="long_open", price=value, key="test-only")
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(webhook(payload))
                self.assertEqual(raised.exception.status_code, 400)
                queue.assert_not_called()

    def test_positive_finite_price_reaches_queue(self):
        payload = WebhookPayload(symbol="BTCUSDT", alert="long_open", price=100.5, key="test-only")
        with patch("app.api.webhook.tradingview_service.add_to_queue", return_value=True) as queue, patch("app.api.webhook.tradingview_service.trigger_queue_processing") as trigger:
            result = asyncio.run(webhook(payload))
        queue.assert_called_once_with("BTCUSDT", "long_open", 100.5)
        trigger.assert_called_once()
        self.assertEqual(result["status"], "success")
