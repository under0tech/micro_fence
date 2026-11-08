import gc
import time
import socket
import ujson

from umqtt.simple import MQTTClient

def find_ha_ip():
    """
    Resolves the local IP address of the Home Assistant server using mDNS.

    Loops indefinitely with a 5-second delay until the hostname 
    'homeassistant.local' resolves via network socket address info.

    :return: 
        The resolved IP address string of the Home Assistant server.
    """

    target_host = "homeassistant.local"
    print(f"[MQTT HA] searching for Home Assistant ({target_host})...")

    while True:
        try:
            addr_info = socket.getaddrinfo(target_host, 1883)
            ip = addr_info[0][-1][0]
            print("[MQTT HA] have HA found on IP:", ip)
            return ip
        except:
            print("[MQTT HA] not found yet, retrying in 5 seconds...")
            time.sleep(5)


class MicroFenceMQTTRepresenter:
    """
    Proxy handler for registering and updating the
    'MicroFence' perimeter security host device
    in Home Assistant via MQTT.
    """

    BROKER = "192.168.1.168"

    def __init__(self, mqtt_user, mqtt_password, 
                            device_id = '000bb0aa',
                            server_ip = "192.168.1.168",
                            devices_config={},
                            on_ha_event=None):
        """
        Initialize MQTT network settings, maps metadata structures,
        defines the Home Assistant device profile, and opens a client connection.

        :param mqtt_user: 
            The username credential for the MQTT broker.
        :param mqtt_password: 
            The password credential for the MQTT broker.
        :param device_id: 
            A unique hardware string identifier (e.g., chip MAC fragment).
        :param server_ip: 
            The IP address of the target MQTT broker.
        :param devices_config: 
            A dictionary mapping MicroFence security device IDs to device types.
            {
                2: "camera",
                3: "pir"
            }
        :param on_ha_event:
            A callback function to be invoked when a message is received from HA.
        """

        self.mqtt_user = mqtt_user
        self.mqtt_password = mqtt_password
        self.device_id = "MicroFence_" + device_id
        self.BROKER = server_ip
        self.devices_config = devices_config
        self.on_ha_event = on_ha_event

        self.devices = {
            "camera": {
                "name": "MicroFence Camera {0} Image",
                "topic": "microfence/{0}_{1}/image",
                "config":"homeassistant/image/{0}_{1}/{1}_camera/config",
                "content_type": "image/jpeg",
                "icon": "mdi:camera"
            },
            "pir": {
                "name": "MicroFence PIR Sensor {0} Event",
                "topic": "microfence/event/{0}_{1}/state",
                "config":"homeassistant/event/{0}_{1}_pir/config",
                "event_types": ["motion_detected"],
                "icon": "mdi:alert-circle"
            }
        }

        self.device = {
            "identifiers": [self.device_id],
            "name": "MicroFence " + device_id,
            "model": "MicroFence",
            "manufacturer": "Greenhouse"
        }

        self.client = MQTTClient(
            client_id=self.device_id.encode(),
            server=self.BROKER,
            user=mqtt_user,
            password=mqtt_password)

        self.client.connect()
        print("[MQTT HA] connected.")

        time.sleep(1)

        if on_ha_event:

            self.control_panel = {
                "config_topic": f"homeassistant/alarm_control_panel/{self.device_id}/config",
                "state_topic": f"microfence/alarm/{self.device_id}/state",
                "command_topic":  f"microfence/alarm/{self.device_id}/set"
            }

            self.control_payload = {
                "unique_id": self.device_id,
                "state_topic": self.control_panel["state_topic"],
                "command_topic": self.control_panel["command_topic"],
                "payload_arm_away": "ARM",
                "payload_disarm": "DISARM",
                "supported_features": ["arm_away"],
                "code_arm_required": False
            }

            self.client.set_callback(self.on_message)
            self.client.publish(self.control_panel["config_topic"], ujson.dumps(self.control_payload), retain=True)
            self.client.subscribe(self.control_panel["command_topic"])
            print("[MQTT HA] command topic subscribed.")


    def on_message(self, topic, msg):
        """
        Handle MQTT commands from the Home Assistant alarm control panel.

        ARM:
            Sets the alarm state to armed_away and triggers the HA event
            callback with "Arm".

        DISARM:
            Sets the alarm state to disarmed and triggers the HA event
            callback with "Disarm".
        """

        command = msg.decode()

        if command == "ARM":
            self.client.publish(self.control_panel["state_topic"], "armed_away", retain=True)
            if self.on_ha_event:
                self.on_ha_event("Arm")
        elif command == "DISARM":
            self.client.publish(self.control_panel["state_topic"], "disarmed", retain=True)
            if self.on_ha_event:
                self.on_ha_event("Disarm")


    def check_messages(self):
        """Check for MQTT messages for a short period."""

        for _ in range(5):
            self.client.check_msg()
            time.sleep(0.6)


    def init_disarmed(self):
        """Initialize the Home Assistant alarm panel into disarmed state."""
        try:
            self.client.publish(self.control_panel["state_topic"], "disarmed", retain=True)
            print("[MQTT HA] init command topic - disarmed.")
            return True
        except:
            return False


    def update_config(self):
        """
        Publishe Home Assistant MQTT Discovery configuration JSON.

        Loop through all configured security devices and post retained
        JSON profiles to the discovery prefix.
        """

        for device_id, device_type in self.devices_config.items():
            if device_type in self.devices:
                device = self.devices[device_type]

                discovery_topic = device["config"].format(self.device_id, device_id)

                payload = {
                    "name": device["name"].format(device_id),
                    "icon": device["icon"],
                    "unique_id": f"{self.device_id}_{device_id}_{device_type}",
                    "device": self.device
                }

                payload["image_topic" if device_type == "camera" else "state_topic"] = device["topic"].format(self.device_id, device_id)

                if device_type == "camera":
                    payload["content_type"] = device["content_type"]

                if device_type == "pir":
                    payload["event_types"] = device["event_types"]

                self.client.publish(
                    discovery_topic,
                    ujson.dumps(payload).encode(),
                    retain=True
                )

        print("[MQTT HA] sensors discovery configured.")


    def update_image_state(self, device_id, file_name):
        """
        Publishes a JPEG image state update.

        :param device_id:
            The device ID.

        :param file_name:
            The JPEG image file name.
        """

        gc.collect()

        with open(file_name, "rb") as file:
            image = file.read()

        topic = self.devices["camera"]["topic"].format(
            self.device_id, device_id)

        self.client.publish(topic, image)

        print(f"[MQTT HA] image from {device_id} published.")


    def event_motion_detected(self, device_id, message):
        """
        Publishes a motion detected event.

        :param device_id:
            The device ID.

        :param message:
            The message from the device.
        """

        payload = {
            "event_type": "motion_detected",
            "device_id": f"{self.device_id}_{device_id}",
            "message": f"Motion detected on {device_id}, message - {message}"
        }

        topic = self.devices["pir"]["topic"].format(
            self.device_id, device_id)

        self.client.publish(
            topic,
            ujson.dumps(payload).encode())

        print(f"[MQTT HA] motion detected on {device_id} published.")


    def disconnect(self):
        """
        Terminates the network socket connection with the MQTT broker.
        """
        
        self.client.disconnect()
        print("[MQTT HA] disconnected.")