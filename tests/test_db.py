import sys
import os
import unittest
from datetime import datetime

# Ensure app path
sys.path.append(os.getcwd())

from app.core import database
from app.core import crud
from app.models.log import Log
from app.models.order import Order
from app.models.alert import Alert

class TestDatabase(unittest.TestCase):
    def setUp(self):
        # Use in-memory DB for testing or separate test file
        # For simplicity in this environment, we use a test file
        self.db_path = os.path.join(os.getcwd(), 'data', 'test_bot.db')
        self.database_url = f"sqlite:///{self.db_path}"
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        database.Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        database.Base.metadata.drop_all(bind=self.engine)
        # os.remove(self.db_path) # Optional: keep for inspection if needed, or remove

    def test_create_log(self):
        log = crud.create_log(self.db, "INFO", "test_func", "test description")
        self.assertIsNotNone(log.id)
        self.assertEqual(log.type, "INFO")
        
        logs = crud.get_logs(self.db)
        self.assertEqual(len(logs), 1)

    def test_create_alert_and_process(self):
        alert = crud.create_alert(self.db, "BTCUSDT", "long_open", 50000.0)
        self.assertFalse(alert.is_processed)
        
        crud.mark_alerts_processed_by_symbol(self.db, "BTCUSDT")
        
        # Refresh
        updated_alert = self.db.query(Alert).filter(Alert.id == alert.id).first()
        self.assertTrue(updated_alert.is_processed)

    def test_order_lifecycle(self):
        order = crud.create_order(self.db, "BTCUSDT", "LONG", 10, 0.1, 5000, 50000.0)
        self.assertTrue(order.is_open)
        
        crud.close_order(self.db, "BTCUSDT", "LONG", 51000.0, 100.0)
        
        updated_order = self.db.query(Order).filter(Order.id == order.id).first()
        self.assertFalse(updated_order.is_open)
        self.assertEqual(updated_order.exit_price, 51000.0)

if __name__ == '__main__':
    unittest.main()
