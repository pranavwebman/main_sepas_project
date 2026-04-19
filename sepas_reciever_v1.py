import network
import espnow
import time
from machine import Pin

# ====== HARDWARE SETUP ======
# Connect the 'S' (Signal) pin of your buzzer to GPIO 15
buzzer = Pin(15, Pin.OUT)
# Ensure it starts OFF
buzzer.value(1) 

# Connect the built-in LED (usually GPIO 2) for visual feedback
led = Pin(2, Pin.OUT)

# ====== ESP-NOW SETUP ======
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect() # Don't connect to a router

e = espnow.ESPNow()
e.active(True)

def alarm_beep(times):
    """Creates a pulsing alarm sound"""
    print("🚨 ALARM TRIGGERED!")
    for _ in range(times):
        buzzer.value(0)
        led.value(1)
        time.sleep(0.2) # Beep duration
        buzzer.value(1)
        led.value(0)
        time.sleep(0.2) # Gap between beeps

print("📡 Receiver is Online. Waiting for SOS...")

# ====== MAIN LOOP ======
while True:
    # Use 0 for non-blocking (check and move on) 
    # or an integer like 100 for a 100ms timeout
    host, msg = e.recv(0) 
    
    if msg:
        if msg == b'SOS_ALERT':
            alarm_beep(10)
        
    time.sleep(0.01)

