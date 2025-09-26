# region ===== INFO ===================================================================================================

# Developer : Ilkay Beydah Saglam
# Website   : https://beydahsaglam.com
# Created   : 2025-08-21
# Version   : Python 3.10

# DESC:
#   This module serves as the entry point for the application.
#   It starts the Telegram bot thread (daemon) and sends a welcome message.
#   The main loop keeps the process alive and forwards any potential errors to the log system.

# FEATURES:
#   - Starting the Telegram bot polling process (SR_Telegram.F_Telegram_Business)
#   - Sending a welcome message with buttons
#   - Ensuring service continuity with an infinite waiting loop
#   - Recording error statuses via MD_Logs

# endregion
# region ===== LIBRARY ================================================================================================

from c_service import sr_b_tradingview as   SR_TradingView
from c_service import sr_e_telegram as      SR_Telegram
from d_model import md_e_logs as            MD_Logs
import time as                              LB_Time
import threading as                         LB_Thread

# endregion
# region ===== VARIABLE ===============================================================================================

Bot_Open: bool = False

# endregion
# region ===== OBJECT =================================================================================================

# endregion
# region ===== FUNCTION ===============================================================================================

def F_Main():
    # DESC: Starts the program
    try:
        global Bot_Open
        if not Bot_Open:
            Bot_Open = True
            SR_TradingView.Bot_Stop = False
            telegram_bot = LB_Thread.Thread(target=SR_Telegram.F_Telegram_Business, daemon=True)
            telegram_bot.start()
            tradingview_bot = LB_Thread.Thread(target=SR_TradingView.F_Tradingview_Business, daemon=True)
            tradingview_bot.start()
            try: 
                SR_Telegram.F_Send_Button("Hello, I am the Binance Bot! I am here for you", [[("Start", "/start")]])
                print("=======================================")
                print("= Bot Started                         =")
                print("=======================================")
            except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Main_Send_Welcome", e)
        while True: LB_Time.sleep(5000)
    except Exception as e: return not MD_Logs.F_Add_Logs("ERROR", "F_Main", e)

if __name__ == "__main__": F_Main()

# endregion