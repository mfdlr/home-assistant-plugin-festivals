import asyncio 
import json 
import logging 
import os
import time 
from typing import Optional 
 
# Importiere die Fridge-Klasse aus deiner fridge.py Datei 
# Stelle sicher, dass fridge.py im selben Verzeichnis liegt oder im PYTHONPATH ist. 
from fridge import Fridge, FridgeData 
 
import paho.mqtt.client as mqtt 

OPTIONS_FILE = "/data/options.json"

def get_addon_config():
    # Verify the options file exists
    if not os.path.exists(OPTIONS_FILE):
        print(f"Error: Configuration file not found at {OPTIONS_FILE}")
        return {}

    try:
        with open(OPTIONS_FILE, "r") as f:
            config = json.load(f)
            return config
    except json.JSONDecodeError:
        print("Error: Could not parse options.json. Invalid JSON format.")
        return {}

# Example usage
config = get_addon_config()

# --- Konfiguration --- 
MQTT_BROKER_HOST = config.get("mqtt_host", "127.0.0.1")
MQTT_BROKER_PORT = config.get("mqtt_port", 1883) 
MQTT_BROKER_USERNAME = config.get("mqtt_username", None) # Optional 
MQTT_BROKER_PASSWORD = config.get("mqtt_password", None) # Optional 

FRIDGE_MAC_ADDRESS = config.get("fridge_mac_address", "00:00:00:00:00:00")
FRIDGE_DEVICE_ID = config.get("fridge_mac_address", "MyFridge")
FRIDGE_VERBOSE = Fconfig.get("fridge_mac_address", False)
 
# MQTT-Topics für Home Assistant Climate Integration 
BASE_TOPIC = f"homeassistant/climate/{FRIDGE_DEVICE_ID}" 
DISCOVERY_TOPIC = f"{BASE_TOPIC}/config" 
STATE_TOPIC = f"{BASE_TOPIC}/state" 
PRESET_MODE_TOPIC = f"{BASE_TOPIC}/preset_mode" 
CURRENT_TEMP_STATE_TOPIC = f"{BASE_TOPIC}/temperature" 
TARGET_TEMP_STATE_TOPIC = f"{BASE_TOPIC}/target_temperature" 
MODE_COMMAND_TOPIC = f"{BASE_TOPIC}/mode/set" 
PRESET_COMMAND_TOPIC = f"{BASE_TOPIC}/preset_mode/set" 
TEMP_COMMAND_TOPIC = f"{BASE_TOPIC}/target_temperature/set" 
 
UPDATE_INTERVAL_SECONDS = 10 # Wie oft der Sensor ausgelesen und Status gesendet wird 
 
# Logging konfigurieren 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 
logger = logging.getLogger(__name__) 
 
# Globale Variable für den MQTT-Client 
mqtt_client = None 
fridge_instance: Optional[Fridge] = None # Um die Fridge-Instanz global zugänglich zu machen 
fridge_data: Optional[FridgeData] = None # Um die Fridge-Daten global zugänglich zu machen 
# Referenz zum asyncio-Event-Loop, um thread-sichere Aufrufe zu ermöglichen 
asyncio_loop: Optional[asyncio.AbstractEventLoop] = None 
 
# --- MQTT Callbacks --- 
def on_connect(client, userdata, flags, rc): 
   if rc == 0:
       logger.info("Mit MQTT Broker verbunden!")
       client.subscribe(MODE_COMMAND_TOPIC)
       client.subscribe(TEMP_COMMAND_TOPIC)
       client.subscribe(PRESET_COMMAND_TOPIC)
       logger.info(f"Abonniert: {MODE_COMMAND_TOPIC}")
       logger.info(f"Abonniert: {TEMP_COMMAND_TOPIC}")
       logger.info(f"Abonniert: {PRESET_COMMAND_TOPIC}")
       publish_ha_discovery() # Discovery-Nachricht nach Verbindung senden
   else:
       logger.error(f"Verbindung zu MQTT Broker fehlgeschlagen, Fehlercode: {rc}")
 
def on_message(client, userdata, msg): 
   global fridge_instance, fridge_data
   topic = msg.topic
   payload = msg.payload.decode()
   logger.info(f"MQTT Nachricht empfangen - Topic: {topic}, Payload: {payload}")
 
   if fridge_instance is None:
       logger.warning("Kühlschrank ist nicht verbunden, Befehl kann nicht ausgeführt werden.")
       return
 
   # Sicherstellen, dass der asyncio_loop verfügbar ist
   if asyncio_loop is None:
       logger.error("Asyncio Event Loop nicht verfügbar, kann Befehl nicht ausführen.")
       return
 
   if topic == MODE_COMMAND_TOPIC:
       if payload == "off":
           fridge_data.powered_on = False
           asyncio.run_coroutine_threadsafe(fridge_instance.set(fridge_data), asyncio_loop)
           logger.info("Kühlschrank ausgeschaltet via MQTT.")
       elif payload == "cool": # Oder "HEAT", "AUTO", je nachdem was dein Kühlschrank unterstützt
           fridge_data.powered_on = True
           asyncio.run_coroutine_threadsafe(fridge_instance.set(fridge_data), asyncio_loop)
           logger.info("Kühlschrank eingeschaltet via MQTT (Modus: COOL).")
       else:
           logger.warning(f"Unbekannter Modus-Befehl: {payload}")
   elif topic == PRESET_COMMAND_TOPIC:
       if payload == "eco":
           fridge_data.run_mode = 1 # Beispielwert für Eco-Modus
           asyncio.run_coroutine_threadsafe(fridge_instance.set(fridge_data), asyncio_loop)
           logger.info("Eco-Modus aktiviert via MQTT.")
       elif payload == "boost":
           fridge_data.run_mode = 0 # Beispielwert für Boost-Modus
           asyncio.run_coroutine_threadsafe(fridge_instance.set(fridge_data), asyncio_loop)
           logger.info("Boost-Modus aktiviert via MQTT.")
       else:
          logger.warning(f"Unbekannter Preset-Modus: {payload}")   
   elif topic == TEMP_COMMAND_TOPIC:
       try:
           target_temp = float(payload)
           # Begrenze die Temperatur auf sinnvolle Werte, die dein Kühlschrank unterstützt
           if -20 <= target_temp <= 20: # Beispiel: 0 bis 20 Grad Celsius
               asyncio.run_coroutine_threadsafe(fridge_instance.set_unit1_target_temperature(int(target_temp)), asyncio_loop)
               logger.info(f"Wunschtemperatur auf {target_temp}°C gesetzt via MQTT.")
           else:
               logger.warning(f"Ungültiger Temperaturbereich: {target_temp}°C")
       except ValueError:
           logger.error(f"Ungültiger Temperatur-Payload: {payload}")
 
# --- Home Assistant Discovery --- 
def publish_ha_discovery(): 
   discovery_payload = {
       "name": f"Kühlschrank {FRIDGE_DEVICE_ID}",
       "unique_id": f"fridge_{FRIDGE_DEVICE_ID}_climate",
       "device": {
           "identifiers": [FRIDGE_DEVICE_ID],
           "name": f"Bluetooth Kühlschrank {FRIDGE_DEVICE_ID}",
           "model": "IceCube 50",
           "manufacturer": "Plug-In Festivals",
       },
       "temperature_unit": "C",
       "min_temp": -20,
       "max_temp": 20,
       "temperature_step": 1,
       "modes": ["off", "cool"],
       'preset_modes': ["eco", "boost"],
       "current_temperature_topic": CURRENT_TEMP_STATE_TOPIC,
       "current_temperature_state_topic": CURRENT_TEMP_STATE_TOPIC, # Redundant, aber oft so verwendet
       "mode_state_topic": STATE_TOPIC,
       "mode_command_topic": MODE_COMMAND_TOPIC,
       'preset_mode_state_topic': f"{BASE_TOPIC}/preset_mode",
       'preset_mode_command_topic': f"{BASE_TOPIC}/preset_mode/set",
       "temperature_command_topic": TEMP_COMMAND_TOPIC,
       "temperature_topic": TARGET_TEMP_STATE_TOPIC,
       "temperature_state_topic": TARGET_TEMP_STATE_TOPIC, # Redundant, aber oft so verwendet
   }
   mqtt_client.publish(DISCOVERY_TOPIC, json.dumps(discovery_payload), qos=0, retain=True)
   logger.info(f"Home Assistant Discovery-Nachricht gesendet an: {DISCOVERY_TOPIC}")
 
# --- Hauptlogik zum Auslesen und Senden --- 
async def fridge_mqtt_loop(): 
   global fridge_instance
   global fridge_data
   while True:
       try:
           # Verbindung zum Kühlschrank herstellen
           if fridge_instance is None:
               logger.info(f"Versuche Verbindung zum Kühlschrank ({FRIDGE_MAC_ADDRESS}) herzustellen...")
               fridge_instance = Fridge(FRIDGE_MAC_ADDRESS, FRIDGE_VERBOSE)
               await fridge_instance.connect()
               logger.info("Kühlschrank verbunden!")
               # Nach erfolgreicher Verbindung erneut Discovery senden, falls HA offline war
               publish_ha_discovery()
 
           # Status auslesen
           status = await fridge_instance.query()
           fridge_data = status
           logger.debug(f"Kühlschrankstatus: {status}")
 
           # Status an MQTT senden
           current_temp = status.unit1.current_temperature
           target_temp = status.unit1.target_temperature
           power_state = status.powered_on
           preset_state = status.run_mode
 
           # Home Assistant "mode" State
           ha_mode = "off"
           if power_state:
               ha_mode = "cool" # Oder "AUTO", "HEAT" etc., je nach Funktion
         
           ha_preset_mode = "boost" if preset_state == 0 else "eco"
 
           if current_temp is not None:
               mqtt_client.publish(CURRENT_TEMP_STATE_TOPIC, str(current_temp), qos=0, retain=True)
           if target_temp is not None:
               mqtt_client.publish(TARGET_TEMP_STATE_TOPIC, str(target_temp), qos=0, retain=True)
         
           mqtt_client.publish(STATE_TOPIC, ha_mode, qos=0, retain=True)
           mqtt_client.publish(PRESET_MODE_TOPIC, ha_preset_mode, qos=0, retain=True)
         
           # Optional: Batteriestatus senden, wenn in Home Assistant gewünscht
           #if 'battery_percent' in status and status['battery_percent'] is not None:
           #    mqtt_client.publish(f"homeassistant/sensor/{FRIDGE_DEVICE_ID}_battery/state", str(status['battery_percent']), qos=0, retain=True)
           #    # Für Discovery eines einfachen Sensors (Battery)
           #    battery_discovery_payload = {
           #        "name": f"Kühlschrank {FRIDGE_DEVICE_ID} Batterie",
           #        "unique_id": f"fridge_{FRIDGE_DEVICE_ID}_battery_sensor",
           #        "device": {
           #            "identifiers": [FRIDGE_DEVICE_ID],
           #            "name": f"Bluetooth Kühlschrank {FRIDGE_DEVICE_ID}",
           #        },
           #        "state_topic": f"homeassistant/sensor/{FRIDGE_DEVICE_ID}_battery/state",
           #        "unit_of_measurement": "%",
           #        "device_class": "battery",
           #        "state_class": "measurement"
           #    }
           #    mqtt_client.publish(f"homeassistant/sensor/{FRIDGE_DEVICE_ID}_battery/config", json.dumps(battery_discovery_payload), qos=0, retain=True)
 
       except Exception as e:
           logger.error(f"Fehler im Hauptloop: {e}")
           if fridge_instance:
               try:
                   # WICHTIG: Klammern und await hinzugefügt!
                   await fridge_instance.disconnect()
                   logger.info("Kühlschrankverbindung sauber getrennt.")
               except Exception as disconnect_e:
                   logger.error(f"Fehler beim Trennen der Kühlschrankverbindung: {disconnect_e}")
         
           fridge_instance = None # Setzt die Instanz zurück, um Neuverbindung zu erzwingen
         
           # 30 Sekunden warten, bevor ein neuer Verbindungsversuch startet
           logger.info("Warte 30 Sekunden bis zum nächsten Verbindungsversuch...")
           await asyncio.sleep(30)
         
       await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
 
# --- Hauptfunktion --- 
async def main(): 
   global mqtt_client, asyncio_loop
   asyncio_loop = asyncio.get_running_loop() # Den aktuellen Event-Loop holen
   mqtt_client = mqtt.Client(client_id=f"fridge_monitor_{FRIDGE_DEVICE_ID}")
 
   if MQTT_BROKER_USERNAME and MQTT_BROKER_PASSWORD:
       mqtt_client.username_pw_set(MQTT_BROKER_USERNAME, MQTT_BROKER_PASSWORD)
 
   mqtt_client.on_connect = on_connect
   mqtt_client.on_message = on_message
 
   mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
   mqtt_client.loop_start() # Startet den MQTT-Client-Loop in einem separaten Thread
 
   await fridge_mqtt_loop() # Startet den AsyncIO-Loop für den Kühlschrank
 
if __name__ == "__main__": 
   try:
       asyncio.run(main())
   except KeyboardInterrupt:
       logger.info("Skript beendet durch Benutzer.")
       if mqtt_client:
           mqtt_client.loop_stop()
           mqtt_client.disconnect()
       if fridge_instance and asyncio_loop and asyncio_loop.is_running():
           asyncio_loop.call_soon_threadsafe(lambda: asyncio_loop.create_task(fridge_instance.disconnect()))
