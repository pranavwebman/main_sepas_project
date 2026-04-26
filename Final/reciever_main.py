import network
import espnow
import time
import socket
from machine import Pin
import gc

# ====== HARDWARE ======
buzzer = Pin(15, Pin.OUT)
buzzer.value(1) # Assuming Active Low
led = Pin(2, Pin.OUT)

# ====== ESP-NOW SETUP ======
sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.disconnect()

e = espnow.ESPNow()
e.active(True)

# ====== WEB SERVER SETUP ======
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='ESP-Now-Monitor', authmode=network.AUTH_WPA_WPA2_PSK, password='12345678')

message_log = []
MAX_LOG = 30 # Reduced slightly to save RAM

def log_message(name, msg):
    t = time.localtime()
    time_str = f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}"
    message_log.append((time_str, name, msg))
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
        try:
            request = client.recv(1024)
            if request and b'GET' in request:
                # 1. Send HTTP Header
                client.send(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n')
                
                # 2. Send HTML Head & Style (Fixed % error)
                client.send(b"""<!DOCTYPE html>
                            <html>
                                <head>
                                    <title>EMRGENCY MONITORING SYSTEM</title>
                                    <meta charset="UTF-8">
                                    <meta http-equiv="refresh" content="5">
                                    <style>
                                        *{
                                            padding:0;
                                            margin:0;
                                            box-sizing: border-box;
                                            }
                                        
                                        body{
                                            background: linear-gradient(to right, blue, rgb(168, 199, 250));
                                            font-family:sans-serif;
                                            padding:20px;
                                        }
                                            
                                        table{
                                            border-collapse:collapse;
                                            width:100%; background:white;
                                        }
                                        
                                        th,td{
                                            border:1px solid #ddd;
                                            padding:12px;
                                            text-align:left;
                                        }
                                        
                                        
                                        th{
                                            background:#2c3e50;
                                            color:white;
                                        }
                                        
                                        tr:nth-child(even){
                                            background:#f2f2f2;
                                        }
                                        
                                        .alert{
                                            background:red !important;
                                            color:white;
                                            font-weight:bold;
                                        }
                                        
                                        header{
                                            background: linear-gradient(to left, blue, black);
                                            text-align: center;
                                            padding: 2rem;
                                            color: white;
                                            }
                                    </style>
                                </head>
                                <body>
                                    <header>
                                        <h1>📡 System Monitor</h1>
                                    </header>
                                    <br>
                                    <table>
                                        <tr>
                                            <th>Time</th>
                                            <th>Device Name</th>
                                            <th>Status</th>
                                        </tr>""")
                
                # 3. Send Log Rows (Iterative sending saves RAM)
                for ts, name, msg in reversed(message_log):
                    is_alert = "ALERT" in msg or "SOS" in msg or "PANIC" in msg
                    cls = ' class="alert"' if is_alert else ''
                    row = f'<tr{cls}><td>{ts}</td><td>{name}</td><td>{msg}</td></tr>'
                    client.send(row.encode())
                
                client.send(b"</table></body></html>")
        except Exception as err:
            print("Web error:", err)
        finally:
            client.close()
    except:
        pass

def alarm_beep(times):
    for _ in range(times):
        buzzer.value(0); led.value(1); time.sleep(0.1)
        buzzer.value(1); led.value(0); time.sleep(0.1)

# ====== MAIN LOOP ======
print("🌐 Web panel at","http://",ap.ifconfig()[0])

while True:
    host, msg = e.recv(0) # Non-blocking receive
    if msg:
        try:
            decoded = msg.decode('utf-8', 'ignore')
            
            # SPLIT LOGIC: Check for the ":" separator we added in the transmitter
            if ":" in decoded:
                dev_name, status = decoded.split(":", 1)
            else:
                dev_name = host.hex(':') # Fallback to MAC if no name sent
                status = decoded
            
            log_message(dev_name, status)
            print(f"Received from {dev_name}: {status}")
            
            # Trigger Alarm for specific keywords
            if any(word in status for word in ["SOS", "FIRE", "IMPACT", "PANIC"]):
                alarm_beep(5)
                
        except Exception as e_err:
            print("Data error:", e_err)
            
    handle_client()
    time.sleep(0.01)
    gc.collect() # Frequent garbage collection to prevent crashes

