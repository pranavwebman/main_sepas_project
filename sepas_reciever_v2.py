import network
import espnow
import time
import socket
from machine import Pin

# ====== HARDWARE ======
buzzer = Pin(15, Pin.OUT)
buzzer.value(1)
led = Pin(2, Pin.OUT)

# ====== ESP-NOW SETUP ======
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect()

e = espnow.ESPNow()
e.active(True)

# ====== WEB SERVER (SoftAP mode) ======
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='ESP-Now-Monitor', authmode=network.AUTH_WPA_WPA2_PSK, password='12345678')
while not ap.active():
    time.sleep(0.1)
print("🌐 Web panel at http://", ap.ifconfig()[0])

message_log = []
MAX_LOG = 50

def log_message(msg):
    t = time.localtime()
    time_str = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    message_log.append((time_str, msg))
    if len(message_log) > MAX_LOG:
        message_log.pop(0)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('0.0.0.0', 80))
server_socket.listen(1)
server_socket.setblocking(False)

def handle_client():
    try:
        client, addr = server_socket.accept()
        client.setblocking(False)
        try:
            request = client.recv(1024)
            if request and request.startswith(b'GET'):
                html = """<!DOCTYPE html>
                <html><head><meta charset="UTF-8"><title>ESP‑NOW Monitor</title>
                <meta http-equiv="refresh" content="5">
                <style>body{background:#111;color:#0f0;font-family:monospace;}
                table{border-collapse:collapse;width:100%%;}
                td,th{border:1px solid #0f0;padding:8px;}
                .alert{color:#f44;}</style></head>
                <body><h1>📡 Received Messages</h1>
                <table><tr><th>Time</th><th>Message</th></tr>"""
                for ts, msg in reversed(message_log):
                    cls = 'class="alert"' if msg == b'SOS_ALERT' else ''
                    html += f'<tr {cls}><td>{ts}</td><td>{msg.decode()}</td></tr>'
                html += f"</table><p>Last {len(message_log)} messages</p></body></html>"
                client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + html.encode())
        except:
            pass
        client.close()
    except:
        pass  # no client waiting

# ====== ALARM (unchanged) ======
def alarm_beep(times):
    print("🚨 ALARM TRIGGERED!")
    for _ in range(times):
        buzzer.value(0); led.value(1); time.sleep(0.2)
        buzzer.value(1); led.value(0); time.sleep(0.2)

# ====== MAIN LOOP ======
print("📡 Receiver ready. Connect to Wi-Fi 'ESP-Now-Monitor' (pw:12345678) and open http://192.168.4.1")
while True:
    host, msg = e.recv(0)
    if msg:
        log_message(msg)
        if msg == b'SOS_ALERT':
            alarm_beep(10)
    handle_client()
    time.sleep(0.01)

