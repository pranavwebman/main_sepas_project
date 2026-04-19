import network
import machine
import socket
from machine import Pin, PWM
import time
import gc
import espnow

# ====== ACCESS POINT CONFIG ======
AP_SSID = "SEPAS_SYSTEM"
AP_PASSWORD = "password123" 

# ====== HARDWARE SETUP ======
button = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)
buzzer = Pin(15, Pin.OUT)
buzzer.value(0)

red = PWM(Pin(21), freq=1000)
green = PWM(Pin(23), freq=1000)
blue = PWM(Pin(2), freq=1000)

red.duty(0)
green.duty(0)
blue.duty(0)

sound_sensor = Pin(4, Pin.IN)
fire_sensor = Pin(14, Pin.IN)

IMPACT_TRIGGER_LEVEL = 1  
FIRE_TRIGGER_LEVEL = 0      

# ====== SYSTEM STATE ======
impact_active = False
fire_active = False         
panic_mode = False
playing_sos = False
manual_sos_active = False  # <--- NEW: Specifically tracks manual button trigger

sos_step = 0
sos_substep = 0
sos_timer = 0
last_trigger_time = 0
DEBOUNCE_MS = 500 

# ====== SETUP ACCESS POINT ======
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=AP_SSID, password=AP_PASSWORD)

while not ap.active():
    time.sleep(1)

ip_address = ap.ifconfig()[0]
print(f"\n✅ ACCESS POINT ACTIVE!")
print(f"1. Connect Phone to WiFi: {AP_SSID}")
print(f"2. Open Browser at: http://{ip_address}:8069")

# ====== NEW: SETUP ESP-NOW (BROADCAST) ======
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect() # Ensure it's not trying to connect to a random router

e = espnow.ESPNow()
e.active(True)

# The universal broadcast MAC address
broadcast_mac = b'\xff\xff\xff\xff\xff\xff'
e.add_peer(broadcast_mac)
print("📡 ESP-NOW Broadcast Ready!")
# ============================================

blue.duty(1000)
time.sleep(3)
blue.duty(0)

# ====== SOS FUNCTIONS ======
def start_sos():
    global playing_sos, sos_step, sos_substep, sos_timer
    if playing_sos or panic_mode:
        return
    print("SOS STARTED")
    
    # --- NEW: SEND ESP-NOW BROADCAST ---
    try:
        # Send a simple byte string. You can change 'SOS_ALERT' to whatever you want.
        e.send(broadcast_mac, b'SOS_ALERT')
        print("📡 SOS Broadcast sent to nearby ESPs!")
    except Exception as err:
        print("Broadcast failed:", err)
    # -----------------------------------
    playing_sos = True
    sos_step = 0
    sos_substep = 0
    sos_timer = time.ticks_ms()

def update_sos():
    global playing_sos, sos_step, sos_substep, sos_timer, impact_active, fire_active, manual_sos_active
    if not playing_sos:
        return
    now = time.ticks_ms()
    if sos_step == 0 or sos_step == 4:
        durations = [200, 200, 200]
        if sos_substep < len(durations):
            if sos_timer == 0 or (now - sos_timer >= durations[sos_substep]):
                if buzzer.value() == 0:
                    buzzer.value(1)
                    green.duty(400) 
                else:
                    buzzer.value(0)
                    green.duty(0)
                    sos_substep += 1
                sos_timer = now
        else:
            sos_step += 1; sos_substep = 0; sos_timer = now
    elif sos_step == 2:
        durations = [500, 500, 500]
        if sos_substep < len(durations):
            if sos_timer == 0 or (now - sos_timer >= durations[sos_substep]):
                if buzzer.value() == 0:
                    buzzer.value(1)
                    red.duty(1023)
                else:
                    buzzer.value(0)
                    red.duty(0)
                    sos_substep += 1
                sos_timer = now
        else:
            sos_step += 1; sos_substep = 0; sos_timer = now
    elif sos_step == 1 or sos_step == 3:
        if now - sos_timer >= 300:
            sos_step += 1; sos_substep = 0; sos_timer = 0
    if sos_step > 4:
        playing_sos = False; impact_active = False; fire_active = False
        manual_sos_active = False # <--- NEW: Reset manual flag when done
        sos_step = 0; buzzer.value(0); red.duty(0); green.duty(0); blue.duty(0)
        print("SOS COMPLETE")

# ====== CHECK SENSORS ======
def check_sensors():
    global impact_active, fire_active, manual_sos_active, last_trigger_time
    now = time.ticks_ms()
    if playing_sos or panic_mode:
        return
    
    # Modified logic to track manual vs sensor
    if button.value() == 0:
        print("MANUAL SOS TRIGGERED")
        manual_sos_active = True # <--- NEW: Mark as manual
        start_sos()
        return
        
    if fire_sensor.value() == FIRE_TRIGGER_LEVEL:
        if not fire_active:
            print("FIRE DETECTED!"); fire_active = True; start_sos(); return
            
    if sound_sensor.value() == IMPACT_TRIGGER_LEVEL:
        if not impact_active and (now - last_trigger_time) > DEBOUNCE_MS:
            print("IMPACT DETECTED!"); impact_active = True; last_trigger_time = now; start_sos()

# ====== WEB SERVER HTML (UNTOUCHED) ======
HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SOS System</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;padding:20px;}
        .container{max-width:500px;margin:0 auto;background:white;border-radius:20px;padding:25px;}
        h1{text-align:center;color:#333;margin-bottom:5px;}
        .status{padding:15px;border-radius:10px;margin-bottom:20px;text-align:center;font-weight:bold;background:#f0f0f0;}
        .status.impact{background:#ff4757;color:white;animation:pulse 0.5s infinite;}
        .status.fire{background:#e67e22;color:white;animation:pulse 0.5s infinite;}
        .status.panic{background:#ff6b6b;color:white;}
        @keyframes pulse{0%{opacity:1;}50%{opacity:0.6;}100%{opacity:1;}}
        button{width:100%;padding:15px;margin:8px 0;font-size:16px;font-weight:bold;border:none;border-radius:10px;cursor:pointer;}
        .sos{background:#ff4757;color:white;}
        .panic{background:#ff8c00;color:white;}
        .panic-off{background:#a8a8a8;color:white;}
        .refresh{background:#2ed573;color:white;}
        .ip{background:#2c3e50;color:white;padding:8px;border-radius:8px;text-align:center;margin-top:15px;font-size:12px;}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 SOS Security</h1>
        <div class="status" id="statusBox"><span id="statusText">✅ System Active</span></div>
        <button class="sos" onclick="fetch('/sos')">🚨 SOS EMERGENCY</button>
        <button class="panic" onclick="fetch('/panic')">⚠️ PANIC ON</button>
        <button class="panic-off" onclick="fetch('/panic_off')">✅ PANIC OFF</button>
        <button class="refresh" onclick="location.reload()">🔄 REFRESH</button>
        <div class="ip">🌐 IP: {ip}</div>
    </div>
    <script>
        function update(){
            fetch('/firedetect').then(r=>r.text()).then(f=>{
                let box=document.getElementById('statusBox');
                let text=document.getElementById('statusText');
                if(f=='FIRE'){
                    box.className='status fire';
                    text.innerHTML='🔥 FIRE DETECTED!';
                } else {
                    fetch('/impact').then(r=>r.text()).then(data=>{
                        if(data=='IMPACT'){
                            box.className='status impact';
                            text.innerHTML='🚨 IMPACT DETECTED!';
                        }else{
                            fetch('/panic_status').then(r=>r.text()).then(p=>{
                                if(p=='PANIC_ON'){
                                    box.className='status panic';
                                    text.innerHTML='⚠️ PANIC MODE';
                                }else{
                                    box.className='status';
                                    text.innerHTML='✅ System Active';
                                }
                            });
                        }
                    });
                }
            });
        }
        setInterval(update, 500);
        update();
    </script>
</body>
</html>
"""

# ====== HANDLE REQUESTS ======
def handle_request(request):
    global panic_mode, playing_sos, impact_active, fire_active, manual_sos_active
    try:
        path = request.split(' ')[1]
    except:
        path = '/'
    
    # NEW ENDPOINT
    if path == '/mansos':
        return "MANSOS" if manual_sos_active else "NORMAL"
        
    elif path == '/sos':
        if not playing_sos and not panic_mode:
            impact_active = True; start_sos()
        return "SOS Started"
    elif path == '/panic':
        panic_mode = True; playing_sos = False; impact_active = False; fire_active = False; manual_sos_active = False
        buzzer.value(0); red.duty(500); green.duty(90); blue.duty(0)
        return "Panic ON"
    elif path == '/sound':
        buzzer.value(1); red.duty(1000); return "Sound ON"
    elif path == '/sound_off':
        buzzer.value(0); red.duty(0); return "Sound OFF"
    elif path == '/panic_off':
        panic_mode = False; red.duty(0); green.duty(0); blue.duty(0)
        return "Panic OFF"
    elif path == '/impact':
        return "IMPACT" if impact_active else "NO_IMPACT"
    elif path == '/firedetect':
        return "FIRE" if fire_active else "NO_FIRE"
    elif path == '/panic_status':
        return "PANIC_ON" if panic_mode else "PANIC_OFF"
    elif path == '/':
        return None
    return "Unknown"

# ====== START SERVER ======
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 8069))
server.listen(5)
server.setblocking(False)

# ====== MAIN LOOP ======
try:
    while True:
        check_sensors()
        if playing_sos:
            update_sos()
        try:
            client, addr = server.accept()
            client.settimeout(0.1)
            try:
                raw_request = client.recv(256)
                if raw_request:
                    request = raw_request.decode()
                    response = handle_request(request)
                    if response is None:
                        html_out = HTML.replace("{ip}", ip_address)
                        client.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html_out.encode())
                    elif response != "Unknown":
                        client.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\n" + response.encode())
            except:
                pass
            finally:
                client.close()
                gc.collect()
        except:
            pass
        time.sleep(0.01)
except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    server.close()
    buzzer.value(0); red.duty(0); green.duty(0); blue.duty(0)

