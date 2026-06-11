import paho.mqtt.client as mqtt
import requests
import json
import os
import time
import logging
import urllib3
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# ─── Deshabilitar advertencias de SSL ────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── Configuración ───────────────────────────────────────────────────────────
MQTT_HOST     = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT     = int(os.getenv("MQTT_PORT", "1883"))
WEBHOOK_URL   = os.getenv("WEBHOOK_URL", "")
COOLDOWN_SECS = int(os.getenv("COOLDOWN_SECS", "10"))
MQTT_CLIENT_ID = "frigate-bridge"

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("frigate-bridge")

# ─── Estado interno ──────────────────────────────────────────────────────────
last_sent = 0

def send_webhook():
    """Envía la petición al webhook de Surveillance Station."""
    global last_sent
    now = time.time()

    if now - last_sent < COOLDOWN_SECS:
        remaining = int(COOLDOWN_SECS - (now - last_sent))
        log.info(f"⏳ Cooldown activo ({remaining}s restantes)")
        return False

    try:
        parsed_url = urlparse(WEBHOOK_URL)
        query_params = parse_qs(parsed_url.query)
        token = query_params.get('token', [None])[0]
        
        if not token:
            log.error("❌ No se encontró token en la URL")
            return False
        
        post_data = {
            "token": token,
            "event": "bark",
            "message": f"🐕 Ladrido detectado en la sala - {datetime.now().strftime('%H:%M:%S')}",
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}",
            data=post_data,
            timeout=5,
            verify=False
        )
        
        if response.status_code == 200:
            log.info(f"✅ Webhook enviado correctamente")
            last_sent = now
            return True
        else:
            log.warning(f"⚠️ Webhook respondió: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        log.error(f"❌ Error en webhook: {e}")
        return False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(f"🟢 Conectado a MQTT: {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe("frigate/sala_tapo/audio/bark")
        client.subscribe("frigate/sala_tapo/audio/dog")
        client.subscribe("frigate/sala_tapo/audio/animal")
        log.info(f"📡 Suscrito a topics: bark, dog, animal")
    else:
        log.error(f"🔴 Error MQTT (código {rc})")

def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje al topic suscrito."""
    global last_sent
    
    try:
        # El payload ya viene como string decodificado
        payload = msg.payload.decode('utf-8').strip()
        topic = msg.topic
        
        log.info(f"📨 {topic} = {payload}")
        
        # Si el mensaje es "ON" (detección activa)
        if payload == "ON":
            log.info(f"🐕 ¡Detección activada! Enviando notificación...")
            send_webhook()
                
    except Exception as e:
        log.error(f"❌ Error: {e}")

def main():
    if not WEBHOOK_URL:
        log.error("❌ ERROR: WEBHOOK_URL no está configurada")
        exit(1)
    
    log.info("=" * 70)
    log.info("🚀 Frigate Bridge v0.5 - Modo ON/OFF")
    log.info("=" * 70)
    log.info(f"📍 MQTT Broker   : {MQTT_HOST}:{MQTT_PORT}")
    log.info(f"⏱️  Cooldown      : {COOLDOWN_SECS}s")
    log.info("=" * 70)
    
    client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            log.info("✅ Escuchando eventos...")
            client.loop_forever()
        except Exception as e:
            log.error(f"❌ Error de conexión: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()