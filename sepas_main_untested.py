import machine
import network
import socket
import time

# --- CONFIGURATION ---
SSID = "YOUR_WIFI_NAME"
PASSWORD = "YOUR_WIFI_PASSWORD"

# Hardware Pins
LED = machine.Pin(2, machine.Pin.OUT)
BUZZER = machine.Pin(4, machine.Pin.OUT)
IMPACT_SENSOR = machine.Pin(15, machine.Pin.IN)
FIRE_SENSOR = machine.Pin(5, machine.Pin.IN)

# State Tracking
remote_sos = False
last_pulse_time = 0
buzzer_state = False

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    while not wlan.isconnected():
        LED.value(not LED.value())
        time.sleep(0.5)
    LED.value(1)
    print("Connected! IP:", wlan.ifconfig()[0])

def start_api():
    global remote_sos, last_pulse_time, buzzer_state
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    
    while True:
        # 1. READ SENSORS (V2 Logic Re-checked)
        is_fire = (FIRE_SENSOR.value() == 0)
        is_impact = (IMPACT_SENSOR.value() == 1)

        # 2. DETERMINE SYSTEM STATE
        if is_fire:
            current_state = "Fire"
        elif is_impact or remote_sos:
            current_state = "Impact"
        else:
            current_state = "Safe"

        # 3. NON-BLOCKING SOS PULSING (The V2 Pulse Logic)
        if current_state != "Safe":
            current_ms = time.ticks_ms()
            # If "Impact", do the 0.3s on / 0.1s off pattern from V2
            if time.ticks_diff(current_ms, last_pulse_time) > 300: 
                buzzer_state = not buzzer_state
                BUZZER.value(1 if buzzer_state else 0)
                last_pulse_time = current_ms
        else:
            BUZZER.value(0)
            remote_sos = False # Auto-reset to safe when sensors clear

        try:
            s.settimeout(0.05) # Super fast timeout for smooth pulsing
            conn, addr = s.accept()
            request = conn.recv(1024).decode()
            
            # --- API ROUTES ---
            if "/impact" in request:
                response = current_state
            elif "/sos" in request:
                remote_sos = True  # Triggered from Mobile App
                response = "SOS_ACK"
            elif "/sound_off" in request:
                remote_sos = False
                BUZZER.value(0)
                response = "RESET_ACK"
            else:
                response = "INVALID"
            
            # Send plain text back for MIT App Inventor
            conn.send('HTTP/1.1 200 OK\nContent-Type: text/plain\n\n' + response)
            conn.close()
            
        except OSError:
            continue

connect_wifi()
start_api()
