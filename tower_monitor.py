#!/usr/bin/env python3

import json
import time
import socket
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# ── Configuration ──────────────────────────────────────────
MQTT_BROKER   = "mqtt.jclab.xyz"
MQTT_PORT     = 1883
MQTT_USER     = "karc-tower"
MQTT_PASSWORD = "KARC146970!"

HEARTBEAT_INTERVAL   = 600   # seconds (10 minutes)
ENVIRONMENT_INTERVAL = 300   # seconds (5 minutes)

TOPIC_HEARTBEAT    = "tower/heartbeat"
TOPIC_ENVIRONMENT  = "tower/environment"
TOPIC_DOOR         = "tower/door"
# ───────────────────────────────────────────────────────────

def get_uptime():
    with open("/proc/uptime", "r") as f:
        seconds = float(f.readline().split()[0])
    return round(seconds / 3600, 2)  # hours

def read_environment():
    # BME280 not yet connected — returns None until sensor is live
    # Will be populated when adafruit-circuitpython-bme280 is wired up
    try:
        import board
        import adafruit_bme280.basic as adafruit_bme280
        i2c = board.I2C()
        bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
        return {
            "temperature_f": round((bme280.temperature * 9/5) + 32, 1),
            "humidity":      round(bme280.relative_humidity, 1),
            "pressure":      round(bme280.pressure, 1),
        }
    except Exception as e:
        print(f"BME280 not available: {e}")
        return None

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker")
    else:
        print(f"MQTT connection failed, code {reason_code}")

def build_client():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="tower-pi")
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.on_connect = on_connect
    return client

def publish(client, topic, payload):
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    msg = json.dumps(payload)
    result = client.publish(topic, msg, qos=1, retain=False)
    print(f"→ {topic}: {msg}")
    return result

def main():
    client = build_client()

    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            client.loop_start()
            time.sleep(2)  # give connection time to establish
            break
        except Exception as e:
            print(f"Connection failed: {e} — retrying in 30s")
            time.sleep(30)

    last_heartbeat   = 0
    last_environment = 0

    while True:
        now = time.time()

        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            publish(client, TOPIC_HEARTBEAT, {
                "status": "online",
                "uptime_hours": get_uptime(),
                "hostname": socket.gethostname(),
            })
            last_heartbeat = now

        if now - last_environment >= ENVIRONMENT_INTERVAL:
            env = read_environment()
            if env:
                publish(client, TOPIC_ENVIRONMENT, env)
            last_environment = now

        time.sleep(10)

if __name__ == "__main__":
    main()
