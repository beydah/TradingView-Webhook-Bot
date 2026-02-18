import sys
import os
import unittest

# Ensure app path
sys.path.append(os.getcwd())

class TestBasic(unittest.TestCase):
    def test_imports(self):
        """
        Verify that all new modules can be imported without error.
        """
        try:
            from app.core import config
            from app.core import logging
            from app.core import state
            from app.services import binance_service
            from app.services import trade_service
            from app.services import transaction_service
            from app.services import telegram_service
            from app.services import tradingview_service
            from app import main
            
            print("Imports successful.")
        except ImportError as e:
            self.fail(f"Import failed: {e}")
            
    def test_config_loading(self):
        """
        Verify that config loads from .env (or defaults).
        """
        from app.core.config import settings
        self.assertIsNotNone(settings.WEBHOOK_IP)
        print(f"Config loaded. IP: {settings.WEBHOOK_IP}")

if __name__ == '__main__':
    unittest.main()
