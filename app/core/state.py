import threading

# Bot State
bot_running: bool = False
bot_stop_event = threading.Event()

# User conversation states (moved from transaction service if needed globally, but keeping here is safer option)
user_states = {}
user_states_lock = threading.Lock()
