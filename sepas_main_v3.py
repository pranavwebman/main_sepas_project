import network
import socket
from machine import Pin, PWM
import time
import gc

# ====== WIFI CONFIG ======
SSID = "Pranav"
PASSWORD = "pranav94"

# ====== HARDWARE SETUP ======
buzzer = Pin(15, Pin.OUT)
buzzer.value(0)

# RGB LED via PWM
red = PWM(Pin(22), freq=1000)
green = PWM(Pin(23), freq=1000)
blue = PWM(Pin(2), freq=1000)

# Initial state: All Off
red.duty(0)
green.duty(0)
blue.duty(0)

sound_sensor = Pin(4, Pin.IN)   # Digital sound sensor
fire_sensor = Pin(14, Pin.IN)    # MQ135 Digital Output

IMPACT_TRIGGER_LEVEL = 1  
FIRE_TRIGGER_LEVEL = 0     

# ====== SYSTEM STATE ======
impact_active = False
fire_active = False        
panic_mode = False
playing_sos = False

# SOS sequence variables
sos_step = 0  # 0:S, 1:pause, 2:O, 3:pause, 4:S
sos_substep = 0
sos_timer = 0

# Debounce
last_trigger_time = 0
DEBOUNCE_MS = 500 

# ====== CONNECT WIFI ======
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
# To lock in your hotspot IP as discussed:
wifi.ifconfig(('10.240.111.202', '255.255.255.0', '10.240.111.1', '8.8.8.8'))
wifi.connect(SSID, PASSWORD)

print("Connecting", end="")
while not wifi.isconnected():
    print(".", end="")
    time.sleep(1)
print("\nConnected!")
ip_address = wifi.ifconfig()[0]
print(f"IP: {ip_address}")
blue.duty(1000)
time.sleep(3)
blue.duty(0)

# ====== SOS FUNCTIONS ======
def start_sos():
    global playing_sos, sos_step, sos_substep, sos_timer
    if playing_sos or panic_mode:
        return
    
    print("SOS STARTED")
    playing_sos = True
    sos_step = 0
    sos_substep = 0
    sos_timer = time.ticks_ms()

def update_sos():
    global playing_sos, sos_step, sos_substep, sos_timer, impact_active, fire_active
    
    if not playing_sos:
        return
    
    now = time.ticks_ms()
    
    # S Part (Steps 0 and 4) - Using Balanced Green
    if sos_step == 0 or sos_step == 4:
        durations = [200, 200, 200]
        if sos_substep < len(durations):
            if sos_timer == 0 or (now - sos_timer >= durations[sos_substep]):
                if buzzer.value() == 0:
                    buzzer.value(1)
                    green.duty(400) # Balanced Green brightness
                else:
                    buzzer.value(0)
                    green.duty(0)
                    sos_substep += 1
                sos_timer = now
        else:
            sos_step += 1
            sos_substep = 0
            sos_timer = now

    # O Part (Step 2) - Using Red
    elif sos_step == 2:
        durations = [500, 500, 500]
        if sos_substep < len(durations):
            if sos_timer == 0 or (now - sos_timer >= durations[sos_substep]):
                if buzzer.value() == 0:
                    buzzer.value(1)
                    red.duty(1023) # Red at full power
                else:
                    buzzer.value(0)
                    red.duty(0)
                    sos_substep += 1
                sos_timer = now
        else:
            sos_step += 1
            sos_substep = 0
            sos_timer = now

    # Pauses (Steps 1 and 3)
    elif sos_step == 1 or sos_step == 3:
        if now - sos_timer >= 300:
            sos_step += 1
            sos_substep = 0
            sos_timer = 0

    # Completion
    if sos_step > 4:
        playing_sos = False
        impact_active = False  
        fire_active = False
        sos_step = 0
        buzzer.value(0)
        red.duty(0)
        green.duty(0)
        blue.duty(0)
        print("SOS COMPLETE")

# ====== CHECK SENSORS ======
def check_sensors():
    global impact_active, fire_active, last_trigger_time
    now = time.ticks_ms()
    
    if playing_sos or panic_mode:
        return
    
    if fire_sensor.value() == FIRE_TRIGGER_LEVEL:
        if not fire_active:
            print("FIRE DETECTED!")
            fire_active = True
            start_sos()
            return

    if sound_sensor.value() == IMPACT_TRIGGER_LEVEL:
        if not impact_active and (now - last_trigger_time) > DEBOUNCE_MS:
            print("IMPACT DETECTED!")
            impact_active = True
            last_trigger_time = now
            start_sos()

# ====== WEB SERVER HTML ======
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
    global panic_mode, playing_sos, impact_active, fire_active
    try:
        path = request.split(' ')[1]
    except:
        path = '/'
    
    if path == '/sos':
        if not playing_sos and not panic_mode:
            impact_active = True
            start_sos()
        return "SOS Started"
    
    elif path == '/panic':
        panic_mode = True
        playing_sos = False
        impact_active = False
        fire_active = False
        buzzer.value(0)
        # YELLOW LOGIC: Full Red + Dim Green
        red.duty(500)
        green.duty(90) 
        blue.duty(0)
        return "Panic ON"

    elif path == '/sound':
        buzzer.value(1)
        red.duty(1000)
        return "Sound ON"
        
    elif path == '/sound_off':
        buzzer.value(0)
        red.duty(0)
        return "Sound OFF"

    elif path == '/panic_off':
        panic_mode = False
        red.duty(0)
        green.duty(0)
        blue.duty(0)
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

print(f"Server running on port 8069")

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
                request = client.recv(256).decode()
                if request:
                    response = handle_request(request)
                    if response is None:
                        html = HTML.replace("{ip}", ip_address)
                        client.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + html.encode())
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
    buzzer.value(0)
    red.duty(0)
    green.duty(0)
    blue.duty(0)

