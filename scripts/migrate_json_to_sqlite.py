import sys
import os
import json
import datetime

# Ensure app path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal, engine, Base
from app.models.log import Log
from app.models.order import Order
from app.models.alert import Alert

def migrate():
    print("Starting migration...")
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        # Migrate Logs
        log_path = os.path.join("e_database", "db_e_logs.json")
        if os.path.exists(log_path):
            print(f"Migrating logs from {log_path}...")
            with open(log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logs = data.get('logs', [])
                for l in logs:
                    try:
                         dt = datetime.datetime.strptime(l.get('datetime', ''), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                         dt = datetime.datetime.utcnow()
                         
                    db_log = Log(
                        datetime=dt,
                        type=l.get('type'),
                        func=l.get('func'),
                        desc=l.get('desc')
                    )
                    db.add(db_log)
            print(f"Migrated {len(logs)} logs.")

        # Migrate Orders
        order_path = os.path.join("e_database", "db_d_orders.json")
        if os.path.exists(order_path):
            print(f"Migrating orders from {order_path}...")
            with open(order_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                orders = data.get('orders', [])
                for o in orders:
                    try:
                         dt = datetime.datetime.strptime(o.get('datetime', ''), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                         dt = datetime.datetime.utcnow()

                    db_order = Order(
                        datetime=dt,
                        symbol=o.get('symbol'),
                        side=o.get('side'),
                        is_open=(str(o.get('open')).lower() == 'true'),
                        leverage=int(float(o.get('leverage') or 1)),
                        quantity_coin=float(o.get('quantity_coin') or 0),
                        quantity_quote=float(o.get('quantity_quote') or 0),
                        entry_price=float(o.get('entry_price') or 0),
                        exit_price=float(o.get('exit_price') or 0) if o.get('exit_price') else None,
                        pnl=float(o.get('pnl') or 0) if o.get('pnl') else None
                    )
                    db.add(db_order)
            print(f"Migrated {len(orders)} orders.")
            
        # Migrate Alerts
        alert_path = os.path.join("e_database", "db_c_alerts.json")
        if os.path.exists(alert_path):
             print(f"Migrating alerts from {alert_path}...")
             with open(alert_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                alerts = data.get('alerts', [])
                for a in alerts:
                    try:
                         dt = datetime.datetime.strptime(a.get('datetime', ''), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                         dt = datetime.datetime.utcnow()
                         
                    db_alert = Alert(
                        datetime=dt,
                        symbol=a.get('symbol'),
                        type=a.get('type'),
                        price=float(a.get('price') or 0),
                        is_processed=(str(a.get('que')).lower() == 'false')
                    )
                    db.add(db_alert)
             print(f"Migrated {len(alerts)} alerts.")

        db.commit()
        print("Migration complete!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
