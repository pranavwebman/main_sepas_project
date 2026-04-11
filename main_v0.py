import network
import socket
from machine import Pin
import time
import gc

# ====== WIFI CONFIG ======
SSID = "Pranav"
PASSWORD = "pranav94"

# ====== HARDWARE SETUP ======
buzzer = Pin(15, Pin.OUT)
buzzer.value(0)
led = Pin(13, Pin.OUT)
led.off()
sound_sensor = Pin(4, Pin.IN)  # Digital sound sensor

IMPACT_TRIGGER_LEVEL = 1  # HIGH = sound detected

# ====== SYSTEM STATE ======
impact_active = False
panic_mode = False
playing_sos = False

# SOS sequence variables
sos_step = 0  # 0:S,1:pause,2:O,3:pause,4:S,5:done
sos_substep = 0
sos_timer = 0

# Debounce
last_trigger_time = 0
DEBOUNCE_MS = 500  # Don't retrigger for 500ms after SOS starts

# ====== CONNECT WIFI ======
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

print("Connecting", end="")
while not wifi.isconnected():
    print(".", end="")
    time.sleep(1)
print("\nConnected!")
ip_address = wifi.ifconfig()[0]
print(f"IP: {ip_address}")

# ====== SOS PATTERN FUNCTIONS ======
def start_sos():
    global playing_sos, sos_step, sos_substep, sos_timer, impact_active, last_trigger_time
    
    if playing_sos or panic_mode:
        return
    
    print("SOS STARTED")
    playing_sos = True
    sos_step = 0
    sos_substep = 0
    sos_timer = time.ticks_ms()
    # Keep impact_active True while playing SOS

def update_sos():
    global playing_sos, sos_step, sos_substep, sos_timer, impact_active
    
    if not playing_sos:
        return
    
    now = time.ticks_ms()
    
    # SOS Pattern: ... --- ...
    if sos_step == 0:  # S: 3 short beeps
        durations = [200, 200, 200]  # ms
        if sos_substep < len(durations):
            if sos_timer == 0:
                buzzer.value(1)
                led.on()
                sos_timer = now
            elif now - sos_timer >= durations[sos_substep]:
                buzzer.value(0)
                led.off()
                sos_substep += 1
                sos_timer = now
                if sos_substep < len(durations):
                    buzzer.value(1)
                    led.on()
                    sos_timer = now
        else:
            sos_step = 1
            sos_substep = 0
            sos_timer = now
    
    elif sos_step == 1:  # Pause
        if sos_timer == 0:
            sos_timer = now
        elif now - sos_timer >= 300:
            sos_step = 2
            sos_substep = 0
            sos_timer = 0
    
    elif sos_step == 2:  # O: 3 long beeps
        durations = [500, 500, 500]
        if sos_substep < len(durations):
            if sos_timer == 0:
                buzzer.value(1)
                led.on()
                sos_timer = now
            elif now - sos_timer >= durations[sos_substep]:
                buzzer.value(0)
                led.off()
                sos_substep += 1
                sos_timer = now
                if sos_substep < len(durations):
                    buzzer.value(1)
                    led.on()
                    sos_timer = now
        else:
            sos_step = 3
            sos_substep = 0
            sos_timer = now
    
    elif sos_step == 3:  # Pause
        if sos_timer == 0:
            sos_timer = now
        elif now - sos_timer >= 300:
            sos_step = 4
            sos_substep = 0
            sos_timer = 0
    
    elif sos_step == 4:  # S: 3 short beeps
        durations = [200, 200, 200]
        if sos_substep < len(durations):
            if sos_timer == 0:
                buzzer.value(1)
                led.on()
                sos_timer = now
            elif now - sos_timer >= durations[sos_substep]:
                buzzer.value(0)
                led.off()
                sos_substep += 1
                sos_timer = now
                if sos_substep < len(durations):
                    buzzer.value(1)
                    led.on()
                    sos_timer = now
        else:
            # SOS COMPLETE
            playing_sos = False
            impact_active = False  # Reset impact after SOS
            sos_step = 0
            sos_substep = 0
            buzzer.value(0)
            led.off()
            print("SOS COMPLETE - Ready for next impact")

# ====== CHECK IMPACT ======
def check_impact():
    global impact_active, last_trigger_time
    
    now = time.ticks_ms()
    
    # Don't detect while playing SOS or in panic mode
    if playing_sos or panic_mode:
        return
    
    # Read sensor
    if sound_sensor.value() == IMPACT_TRIGGER_LEVEL:
        # Debounce check
        if not impact_active and (now - last_trigger_time) > DEBOUNCE_MS:
            print("IMPACT DETECTED!")
            impact_active = True
            last_trigger_time = now
            start_sos()

# ====== MINIMAL HTML ======
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
        .subtitle{text-align:center;color:#666;margin-bottom:20px;font-size:12px;}
        .status{padding:15px;border-radius:10px;margin-bottom:20px;text-align:center;font-weight:bold;background:#f0f0f0;}
        .status.impact{background:#ff4757;color:white;animation:pulse 0.5s infinite;}
        .status.panic{background:#ff6b6b;color:white;}
        @keyframes pulse{0%{opacity:1;}50%{opacity:0.6;}100%{opacity:1;}}
        button{width:100%;padding:15px;margin:8px 0;font-size:16px;font-weight:bold;border:none;border-radius:10px;cursor:pointer;}
        .sos{background:#ff4757;color:white;font-size:20px;}
        .panic{background:#ff8c00;color:white;}
        .panic-off{background:#a8a8a8;color:white;}
        .refresh{background:#2ed573;color:white;}
        .info{background:#f8f9fa;padding:15px;border-radius:10px;margin-top:15px;text-align:center;}
        .ip{background:#2c3e50;color:white;padding:8px;border-radius:8px;text-align:center;margin-top:15px;font-size:12px;}
        .footer{text-align:center;margin-top:20px;color:#999;font-size:10px;}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 SOS Security</h1>
        <div class="subtitle">Instant Impact Detection</div>
        <div class="status" id="statusBox"><span id="statusText">✅ System Active</span></div>
        <button class="sos" onclick="fetch('/sos')">🚨 SOS EMERGENCY</button>
        <button class="panic" onclick="fetch('/panic')">⚠️ PANIC ON</button>
        <button class="panic-off" onclick="fetch('/panic_off')">✅ PANIC OFF</button>
        <button class="refresh" onclick="location.reload()">🔄 REFRESH</button>
        <div class="info">
            <strong>Status:</strong><br>
            <span id="impactInfo">No Impact</span>
        </div>
        <div class="ip">🌐 IP: {ip}</div>
        <div class="footer">Impact = SOS Morse | Auto-reset after SOS</div>
    </div>
    <script>
        function update(){
            fetch('/impact').then(r=>r.text()).then(data=>{
                let box=document.getElementById('statusBox');
                let text=document.getElementById('statusText');
                let info=document.getElementById('impactInfo');
                if(data=='IMPACT'){
                    box.className='status impact';
                    text.innerHTML='🚨 IMPACT DETECTED!';
                    info.innerHTML='⚠️ IMPACT ACTIVE ⚠️';
                }else{
                    fetch('/panic_status').then(r=>r.text()).then(p=>{
                        if(p=='PANIC_ON'){
                            box.className='status panic';
                            text.innerHTML='⚠️ PANIC MODE';
                        }else{
                            box.className='status';
                            text.innerHTML='✅ System Active';
                        }
                        info.innerHTML='✓ No Impact';
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
    global panic_mode, playing_sos, impact_active
    
    try:
        path = request.split(' ')[1]
    except:
        path = '/'
    
    if path == '/sos':
        if not playing_sos and not panic_mode:
            impact_active = True
            start_sos()
            return "SOS Started"
        return "Busy"
    
    elif path == '/panic':
        if not panic_mode:
            panic_mode = True
            playing_sos = False
            impact_active = False
            buzzer.value(0)
            led.on()
        return "Panic ON"
    
    elif path == '/panic_off':
        if panic_mode:
            panic_mode = False
            led.off()
        return "Panic OFF"
    
    elif path == '/panic_status':
        return "PANIC_ON" if panic_mode else "PANIC_OFF"
    
    elif path == '/impact':
        return "IMPACT" if impact_active else "NO_IMPACT"
    
    elif path == '/sound':
        buzzer.value(1)
        
    elif path == '/sound_off':
        buzzer.value(0)
    
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
print("System ready - Impact detection active")

# ====== MAIN LOOP ======
try:
    while True:
        # Check for impact
        check_impact()
        
        # Update SOS playback
        if playing_sos:
            update_sos()
        
        # Handle web requests
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
                    else:
                        client.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
            except:
                pass
            finally:
                client.close()
                gc.collect()
        except:
            pass
        
        time.sleep(0.01)  # Small delay to prevent CPU hogging

except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    server.close()
    buzzer.value(0)
    led.off()
    print("System stopped")

