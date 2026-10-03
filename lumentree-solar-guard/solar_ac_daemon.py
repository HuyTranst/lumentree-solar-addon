#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOLAR AC GUARD BACKGROUND DAEMON - HOME ASSISTANT
Chạy nền 24/7 tự động giám sát Lumentree Solar mỗi 2 giây
Gửi thông báo trực tiếp vào Home Assistant (persistent_notification & notify.notify)
"""

import os
import sys
import time
import json
import struct
import datetime
import requests
import paho.mqtt.client as mqtt

# Paths
BASE_DIR = "/homeassistant" if os.path.exists("/homeassistant") else "/config"
CONFIG_PATH = os.path.join(BASE_DIR, "www/solar_ac/config.json")
STATUS_PATH = os.path.join(BASE_DIR, "www/solar_ac/status.json")
LOG_PATH = os.path.join(BASE_DIR, "www/solar_ac/daemon.log")

# Home Assistant Token & API
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
if SUPERVISOR_TOKEN:
    HA_URL = "http://supervisor/core"
    HA_TOKEN = SUPERVISOR_TOKEN
else:
    HA_URL = os.environ.get("HA_URL", "http://homeassistant:8123")
    HA_TOKEN = os.environ.get("HA_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiYzZmZGNiN2NjNDc0ODAwYjIyOTIzYjc4YjIyNWVhZiIsImlhdCI6MTc4ODI0MDMwNSwiZXhwIjoyMTAzNjAwMzA1fQ.sKrjqR-9F7cQpEhBF7ugLxsL6HjVIGTOwBdw_8T9WQs")

HA_HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json"
}

DEFAULT_CONFIG = {
    "deviceId": "H250521206",
    "checkVol": True,
    "thresholdVol": 300.0,
    "checkCurrent": True,
    "thresholdCurrent": 1.0,
    "checkPower": True,
    "thresholdPower": 1000.0,
    "checkConsecutive": 10,
    "soundEnabled": True,
    "notifyStartTime": "09:00",
    "notifyEndTime": "16:00"
}

# Current State
config = dict(DEFAULT_CONFIG)
telemetry = {
    "pv1Voltage": 0.0,
    "pv1Current": 0.0,
    "pv1Power": 0,
    "gridPower": 0,
    "gridStatus": "Cân bằng",
    "loadPower": 0,
    "lastUpdate": None
}

currentAlertState = "NONE"   # 'NONE', 'INSUFFICIENT', 'SUFFICIENT'
consecutiveLowCount = 0
consecutiveGoodCount = 0
lastNotificationMsg = ""
lastNotificationTime = ""
alertHistory = []

mqtt_client = None
last_packet_time = 0

def log(msg):
    t_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{t_str}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def load_config():
    global config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                config.update(data)
        except Exception as e:
            log(f"Error loading config.json: {e}")
    else:
        # Create default
        save_config()

    # Also sync with HA input_datetime entities if reachable
    try:
        r_start = requests.get(f"{HA_URL}/api/states/input_datetime.solar_ac_notify_start_time", headers=HA_HEADERS, timeout=1.5)
        if r_start.ok:
            st = r_start.json().get("state")
            if st and ":" in st:
                config["notifyStartTime"] = st[:5]
        r_end = requests.get(f"{HA_URL}/api/states/input_datetime.solar_ac_notify_end_time", headers=HA_HEADERS, timeout=1.5)
        if r_end.ok:
            et = r_end.json().get("state")
            if et and ":" in et:
                config["notifyEndTime"] = et[:5]
    except Exception:
        pass

def save_config():
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Error saving config.json: {e}")


def push_ha_sensors():
    try:
        url_base = f"{HA_URL}/api/states"
        sensors = {
            "sensor.lumentree_pv1_power": {
                "state": str(telemetry["pv1Power"]),
                "attributes": {
                    "unit_of_measurement": "W",
                    "device_class": "power",
                    "state_class": "measurement",
                    "friendly_name": "Lumentree PV1 Power",
                    "icon": "mdi:solar-power"
                }
            },
            "sensor.lumentree_pv1_voltage": {
                "state": str(telemetry["pv1Voltage"]),
                "attributes": {
                    "unit_of_measurement": "V",
                    "device_class": "voltage",
                    "state_class": "measurement",
                    "friendly_name": "Lumentree PV1 Voltage",
                    "icon": "mdi:flash"
                }
            },
            "sensor.lumentree_pv1_current": {
                "state": str(telemetry["pv1Current"]),
                "attributes": {
                    "unit_of_measurement": "A",
                    "device_class": "current",
                    "state_class": "measurement",
                    "friendly_name": "Lumentree PV1 Current",
                    "icon": "mdi:current-ac"
                }
            },
            "sensor.lumentree_grid_power": {
                "state": str(telemetry["gridPower"]),
                "attributes": {
                    "unit_of_measurement": "W",
                    "device_class": "power",
                    "state_class": "measurement",
                    "friendly_name": "Lumentree Grid Power",
                    "icon": "mdi:transmission-tower"
                }
            },
            "sensor.lumentree_home_load": {
                "state": str(telemetry["loadPower"]),
                "attributes": {
                    "unit_of_measurement": "W",
                    "device_class": "power",
                    "state_class": "measurement",
                    "friendly_name": "Lumentree Home Load",
                    "icon": "mdi:home-lightning"
                }
            }
        }
        for entity_id, payload in sensors.items():
            requests.post(f"{url_base}/{entity_id}", headers=HA_HEADERS, json=payload, timeout=1.5)
    except Exception:
        pass

def save_status():
    push_ha_sensors()
    try:
        os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
        status_data = {
            "pv1Voltage": telemetry["pv1Voltage"],
            "pv1Current": telemetry["pv1Current"],
            "pv1Power": telemetry["pv1Power"],
            "gridPower": telemetry["gridPower"],
            "gridStatus": telemetry["gridStatus"],
            "loadPower": telemetry["loadPower"],
            "currentAlertState": currentAlertState,
            "consecutiveLowCount": consecutiveLowCount,
            "consecutiveGoodCount": consecutiveGoodCount,
            "maxCount": config.get("checkConsecutive", 10),
            "notifyStartTime": config.get("notifyStartTime", "09:00"),
            "notifyEndTime": config.get("notifyEndTime", "16:00"),
            "lastNotificationMsg": lastNotificationMsg,
            "lastNotificationTime": lastNotificationTime,
            "lastUpdate": datetime.datetime.now().strftime("%H:%M:%S %d/%m/%Y"),
            "isDaemonActive": True,
            "alertHistory": alertHistory[:10]
        }
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        pass

def send_ha_notification(title, message, is_low=True):
    notif_id = "solar_ac_alert"
    # 1. Persistent Notification inside HA
    try:
        url = f"{HA_URL}/api/services/persistent_notification/create"
        payload = {
            "title": title,
            "message": message,
            "notification_id": notif_id
        }
        resp = requests.post(url, headers=HA_HEADERS, json=payload, timeout=5)
        log(f"HA Persistent Notification sent: {resp.status_code}")
    except Exception as e:
        log(f"Error sending persistent notification: {e}")

    # 2. Mobile Push Notification via notify.notify & notify.my_home
    for target in ["notify/notify", "notify/my_home"]:
        try:
            url_notify = f"{HA_URL}/api/services/{target}"
            payload_notify = {
                "title": title,
                "message": message,
                "data": {
                    "tag": notif_id,
                    "color": "#ef4444" if is_low else "#10b981"
                }
            }
            resp2 = requests.post(url_notify, headers=HA_HEADERS, json=payload_notify, timeout=5)
            log(f"HA Mobile Notify ({target}) sent: {resp2.status_code}")
        except Exception as e:
            log(f"Error sending mobile notify ({target}): {e}")

    # 3. Update input_select.solar_ac_state if entity exists in HA
    try:
        url_state = f"{HA_URL}/api/services/input_select/select_option"
        requests.post(url_state, headers=HA_HEADERS, json={
            "entity_id": "input_select.solar_ac_state",
            "option": "INSUFFICIENT" if is_low else "SUFFICIENT"
        }, timeout=5)
    except Exception:
        pass

def crc16_modbus(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return struct.pack("<H", crc)

def create_read_command(start_addr=0, count=95):
    header = bytes([0x01, 0x03, (start_addr >> 8) & 0xFF, start_addr & 0xFF, (count >> 8) & 0xFF, count & 0xFF])
    return header + crc16_modbus(header)

def parse_modbus_payload(payload: bytes):
    hex_str = payload.hex()
    if "2b2b2b2b" in hex_str:
        hex_str = hex_str.split("2b2b2b2b")[1]
    if not hex_str.startswith("0103"):
        return False
    data_len = int(hex_str[4:6], 16)
    reg_bytes = bytes.fromhex(hex_str[6:6 + data_len * 2])
    
    def get_u16(addr):
        offset = addr * 2
        if offset + 2 <= len(reg_bytes):
            return struct.unpack(">H", reg_bytes[offset:offset+2])[0]
        return 0

    def get_i16(addr):
        offset = addr * 2
        if offset + 2 <= len(reg_bytes):
            return struct.unpack(">h", reg_bytes[offset:offset+2])[0]
        return 0

    pv1_v = get_u16(20)
    pv1_p = get_u16(22)
    pv1_i = round(pv1_p / pv1_v, 2) if pv1_v > 0 else 0.0
    grid_w = get_i16(59)
    load_w = get_u16(67)
    
    telemetry["pv1Voltage"] = float(pv1_v)
    telemetry["pv1Power"] = int(pv1_p)
    telemetry["pv1Current"] = float(pv1_i)
    telemetry["gridPower"] = int(grid_w)
    telemetry["loadPower"] = int(load_w)
    
    if grid_w > 5:
        telemetry["gridStatus"] = "Nhập lưới EVN"
    elif grid_w < -5:
        telemetry["gridStatus"] = "Đẩy lưới"
    else:
        telemetry["gridStatus"] = "Cân bằng (Zero)"
        
    telemetry["lastUpdate"] = datetime.datetime.now()
    return True

def evaluate_conditions():
    global currentAlertState, consecutiveLowCount, consecutiveGoodCount, lastNotificationMsg, lastNotificationTime
    
    v = telemetry["pv1Voltage"]
    i = telemetry["pv1Current"]
    p = telemetry["pv1Power"]
    
    chk_v = config.get("checkVol", True)
    chk_i = config.get("checkCurrent", True)
    chk_p = config.get("checkPower", True)
    
    th_v = float(config.get("thresholdVol", 300))
    th_i = float(config.get("thresholdCurrent", 1.0))
    th_p = float(config.get("thresholdPower", 1000))
    max_c = int(config.get("checkConsecutive", 10))
    
    if not (chk_v or chk_i or chk_p):
        return
        
    is_low = (not chk_v or v < th_v) and (not chk_i or i < th_i) and (not chk_p or p < th_p)
    is_good = (not chk_v or v >= th_v) and (not chk_i or i >= th_i) and (not chk_p or p >= th_p)
    
    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%H:%M:%S")
    now_hm = now_dt.strftime("%H:%M")

    # Time Window Check (Default: 09:00 - 16:00)
    start_t = config.get("notifyStartTime", "09:00")
    end_t = config.get("notifyEndTime", "16:00")
    is_in_time_window = (start_t <= now_hm <= end_t)
    
    # CASE 1: LOW SOLAR CONDITION (THIẾU ĐIỆN)
    if is_low:
        consecutiveLowCount += 1
        consecutiveGoodCount = 0
        
        if consecutiveLowCount >= max_c:
            # ANTI-SPAM: Only alert once when entering INSUFFICIENT state
            if currentAlertState != "INSUFFICIENT":
                currentAlertState = "INSUFFICIENT"
                title = "⚠️ Cảnh Báo Solar"
                msg = f"Solar Không đủ điện yêu cầu tắt máy lạnh\n(Điện áp PV1: {v:.0f}V, Dòng: {i:.1f}A, Công suất: {p}W lúc {now_str})"
                log(f">>> TRIGGER ALERT: {msg} (In window: {is_in_time_window})")
                if is_in_time_window:
                    send_ha_notification(title, msg, is_low=True)
                else:
                    log(f"Alert muted: outside notification window ({start_t} - {end_t})")
                
                lastNotificationMsg = "Solar Không đủ điện yêu cầu tắt máy lạnh"
                lastNotificationTime = now_str
                alertHistory.insert(0, {
                    "time": now_str,
                    "type": "low",
                    "msg": lastNotificationMsg + ("" if is_in_time_window else " (Ngoài khung giờ)"),
                    "metrics": f"PV1: {v:.0f}V · {i:.1f}A · {p}W"
                })

    # CASE 2: GOOD SOLAR CONDITION (ĐỦ ĐIỆN)
    elif is_good:
        consecutiveGoodCount += 1
        consecutiveLowCount = 0
        
        if consecutiveGoodCount >= max_c:
            # ANTI-SPAM: Only alert once when entering SUFFICIENT state
            if currentAlertState != "SUFFICIENT":
                currentAlertState = "SUFFICIENT"
                title = "✅ Thông Báo Solar"
                msg = f"Solar đạt mức yêu cầu có thể mở máy lạnh\n(Điện áp PV1: {v:.0f}V, Dòng: {i:.1f}A, Công suất: {p}W lúc {now_str})"
                log(f">>> TRIGGER ALERT: {msg} (In window: {is_in_time_window})")
                if is_in_time_window:
                    send_ha_notification(title, msg, is_low=False)
                else:
                    log(f"Alert muted: outside notification window ({start_t} - {end_t})")
                
                lastNotificationMsg = "Solar đạt mức yêu cầu có thể mở máy lạnh"
                lastNotificationTime = now_str
                alertHistory.insert(0, {
                    "time": now_str,
                    "type": "good",
                    "msg": lastNotificationMsg + ("" if is_in_time_window else " (Ngoài khung giờ)"),
                    "metrics": f"PV1: {v:.0f}V · {i:.1f}A · {p}W"
                })

    else:
        consecutiveLowCount = 0
        consecutiveGoodCount = 0

def fetch_http_fallback():
    dev_id = config.get("deviceId", "H250521206")
    try:
        url = f"https://lumentree.net/api/realtime/{dev_id}"
        resp = requests.get(url, timeout=3)
        if resp.ok:
            d = resp.json().get("data", {})
            pv1_v = d.get("pv1Voltage", 0)
            pv1_p = d.get("pv1Power", 0)
            pv1_i = round(pv1_p / pv1_v, 2) if pv1_v > 0 else 0.0
            
            telemetry["pv1Voltage"] = float(pv1_v)
            telemetry["pv1Power"] = int(pv1_p)
            telemetry["pv1Current"] = float(pv1_i)
            telemetry["gridPower"] = int(d.get("gridPowerFlow", 0))
            telemetry["loadPower"] = int(d.get("homeLoad", 0))
            telemetry["lastUpdate"] = datetime.datetime.now()
            
            evaluate_conditions()
            save_status(); push_ha_sensors()
    except Exception as e:
        pass

def on_connect(client, userdata, flags, rc):
    dev_id = config.get("deviceId", "H250521206")
    sub_topic = f"reportApp/{dev_id}"
    log(f"Connected to Lumentree MQTT Broker. Subscribing to {sub_topic}")
    client.subscribe(sub_topic, qos=1)

def on_message(client, userdata, msg):
    global last_packet_time
    last_packet_time = time.time()
    try:
        if parse_modbus_payload(msg.payload):
            evaluate_conditions()
            save_status(); push_ha_sensors()
    except Exception as e:
        log(f"Error parsing MQTT message: {e}")

def main():
    global mqtt_client, last_packet_time
    log("=== KHỞI ĐỘNG SOLAR AC GUARD DAEMON (Home Assistant) ===")
    
    load_config()
    dev_id = config.get("deviceId", "H250521206")
    pub_topic = f"listenApp/{dev_id}"
    
    client_id = f"ha-ac-daemon-{int(time.time())}"
    mqtt_client = mqtt.Client(client_id=client_id, transport="websockets")
    mqtt_client.ws_set_options(path="/mqtt")
    mqtt_client.username_pw_set("appuser", "app666")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    try:
        mqtt_client.connect("lesvr.suntcn.com", 8083, 60)
        mqtt_client.loop_start()
    except Exception as e:
        log(f"MQTT connect error: {e}")
        
    last_config_check = 0
    
    while True:
        try:
            # 1. Reload config periodically
            now = time.time()
            if now - last_config_check > 5:
                load_config()
                last_config_check = now
            
            # 2. Publish read request every 2s
            cmd = create_read_command(0, 95)
            try:
                mqtt_client.publish(pub_topic, cmd, qos=1)
            except Exception:
                pass
                
            # 3. Fallback to HTTP API if no MQTT packet for > 8s
            if now - last_packet_time > 8:
                fetch_http_fallback()
            
            save_status(); push_ha_sensors()
            time.sleep(2.0)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f"Daemon loop exception: {e}")
            time.sleep(2.0)

    log("Solar AC Guard Daemon stopped.")
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()

if __name__ == "__main__":
    main()