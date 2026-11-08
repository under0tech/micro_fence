import utime
import ubinascii

import definitions as vars

from radio import RadioHC12
from skyfall import Skyfall
from wifiwc import WiFiWc
from telegawc import TelegaWc
from mqtt_representer import MicroFenceMQTTRepresenter, find_ha_ip

from machine import Pin

# -------------------------
# Configuration
# -------------------------
led = Pin(vars.NETWORK_LED_PIN, Pin.OUT)

# -------------------------
# WiFi
# -------------------------
wifi_client = WiFiWc(hostname=vars.WIFI_CLIENT_HOSTNAME,
                    network=vars.WIFI_NETWORK_NAME,
                    password=vars.WIFI_NETWORK_PASSWORD)

# -------------------------
# Telega
# -------------------------
telegawc_client = TelegaWc(
    telegram_host=vars.TELEGRAM_HOST,
    telegram_bot_id=vars.TELEGRAM_BOT_ID,
    telegram_chat_id=vars.TELEGRAM_CHAT_ID)

# -------------------------
# Radio HC-12
# -------------------------
server_radio = RadioHC12(uart_id=vars.RADIO_UART_ID, 
                        tx=vars.RADIO_TX, 
                        rx=vars.RADIO_RX, 
                        baudrate=vars.RADIO_BAUDRATE, 
                        my_id=vars.RADIO_MY_ID, 
                        allowed_devices=vars.RADIO_ALLOWED_DEVICES)

protocol = Skyfall(radio_instance=server_radio, 
                   encryption_keys=vars.SERVER_KEYS)

def protocol_receiver_callback(msg_type, value):
    print(f'[RadiO] we have receieved: {msg_type}: {value}')
    if vars.TELEGRAM_NEEDS_REPORT:
        telegram_queue.append((msg_type, value))
    if vars.MQTT_NEEDS_REPORT:
        mqtt_queue.append((msg_type, value))

# -------------------------
# Home Assistant
# -------------------------
def on_ha_event(cmd):
    print(f'[MQTT HA] command receieved: {cmd}')
    
    text = cmd
    
    if text == 'Arm' or text == 'Disarm':
        for dst_id, key in vars.SERVER_KEYS.items():
            light_signal(signal_reply_start_sending)
            print(f'[RadiO] sending command to {dst_id} - {text}')
            protocol.broadcast_secured_message(dst_id, text)
            utime.sleep(0.4)
            light_signal(signal_reply_end_sending)

# -------------------------
# Light signals
# -------------------------
signal_init = [
    (1, 0.15), (0, 0.15),
    (1, 0.15), (0, 0.15),
    (1, 0.15), (0, 0.15),
    (1, 3), (0, 0.21)
]

signal_wifi_connect = [
    (1, 0.7), (0, 0.2),
    (1, 0.18), (0, 0.2),
    (1, 0.18)
]

signal_wifi_reconect = [
    (1, 0.5), (0, 0.5),
    (1, 0.5), (0, 0.5),
    (1, 0.5), (0, 0.5),
    (1, 0.5), (0, 0.5),
    (1, 0.5), (0, 0.5),
]

signal_start_sending = [
    (1, 0.18), (0, 0.7), (1, 0.5)
]

signal_end_sending = [
    (0, 0.21), (1, 0.4), (0, 0.23), 
    (1, 0.18), (0, 0.21)
]

signal_reply_start_sending = [
    (1, 1), (0, 0.4), (1, 0.6)
]

signal_reply_end_sending = [
    (0, 0.21), (1, 1), (0, 0.4),
    (1, 0.6), (0, 0.21)
]

signal_ha_start_sending = [
    (1, 1), (0, 0.4), (1, 0.6)
]

signal_ha_end_sending = [
    (0, 0.21), (1, 1), (0, 0.4),
    (1, 0.6), (0, 0.21)
]

def light_led(value, duration):
    led.value(value)
    utime.sleep(duration)
    utime.sleep(0.03)

def light_signal(signal):
    for value, duration in signal:
        light_led(value, duration)

# -------------------------
# Init
# -------------------------
light_signal(signal_init)

light_signal(signal_wifi_connect)
wifi_client.connect(timeout=vars.WIFI_CONNECTION_TIMEOUT)

if wifi_client.wifi.isconnected():
    utime.sleep(2)
    mac_str = ubinascii.hexlify(wifi_client.wifi.config('mac')).decode()
    device_id = f"{mac_str}"
    print(f'MAC-address (decoded): {device_id}\n')

led.off()

# -------------------------
# Main loop
# -------------------------
offset = 0
telegram_queue = []
mqtt_queue = []
ha_ip = None
ha_init_disarmed = False

telegram_last_time = (utime.ticks_ms() - 
                      vars.TELEGRAM_UPDATES_TIMEOUT_MS)
mqtt_last_time = (utime.ticks_ms() - 
                      vars.MQTT_UPDATES_TIMEOUT_MS)

while True:
    print('...')
    led.off()

    try:
        # --- RADIO HC-12 UART LISTENING ---
        last_uart_time = utime.ticks_ms()
        while (utime.ticks_diff(
            utime.ticks_ms(), last_uart_time) <= vars.RADIO_UART_TIMEOUT_MS):
            try:
                if server_radio.uart.any() != 0:
                    protocol.read_secured_packages(file_prefix='radio_file_',
                                                file_ext='jpg',
                                                on_message=protocol_receiver_callback,
                                                uart_timeout=vars.RADIO_UART_TIMEOUT_MS)
                    last_uart_time = utime.ticks_ms()
            except: pass
            utime.sleep_ms(5)

        # --- END RADIO HC-12 UART LISTENING ---

        # --- TELEGRAM & NETWORK EXECUTION ---
        if vars.TELEGRAM_NEEDS_REPORT and utime.ticks_diff(
            utime.ticks_ms(), telegram_last_time) >= vars.TELEGRAM_UPDATES_TIMEOUT_MS:
            if wifi_client.reconnect(timeout=vars.WIFI_CONNECTION_TIMEOUT):           
                
                telegram_last_time = utime.ticks_ms()

                # Getting updates from Telegram and reaction
                try:
                    light_signal(signal_start_sending)
                    res = telegawc_client.get_updates(offset=offset)
                    light_signal(signal_end_sending)
                    if res is not None:
                        sender_id, update_id, text = res
                        offset = update_id + 1
                        reply_text = ''
                        if str(sender_id) == vars.TELEGRAM_CHAT_ID:
                            if text == 'Arm':
                                reply_text = f'Arming ...'
                            elif text == 'Disarm':
                                reply_text = f'Disarming ...'
                            else:
                                reply_text = f'Unknown command {text}'
                        else:
                            reply_text = f'Not authorized sender {sender_id} on update {update_id}'

                        if reply_text != '':
                            light_signal(signal_reply_start_sending)
                            telegawc_client.send_message(
                                f'*[{vars.WIFI_CLIENT_HOSTNAME} {device_id}]*: {reply_text}')
                            light_signal(signal_reply_end_sending)

                        if text == 'Arm' or text == 'Disarm':
                            for dst_id, key in vars.SERVER_KEYS.items():
                                light_signal(signal_reply_start_sending)
                                protocol.broadcast_secured_message(dst_id, text)
                                utime.sleep(0.4)
                                light_signal(signal_reply_end_sending)
                except: pass

                # Executing queue 
                while len(telegram_queue) > 0:
                    try:
                        msg_type, msg_val = telegram_queue.pop(0)

                        led.on()
                        if msg_type == Skyfall.MSG_FILE:
                            telegawc_client.send_photo(
                                            msg_val, 
                                            f'[{vars.WIFI_CLIENT_HOSTNAME} {device_id}]: file received - {msg_val}')
                        elif msg_type == Skyfall.MSG_TEXT:
                            telegawc_client.send_message(
                                f'*[{vars.WIFI_CLIENT_HOSTNAME} {device_id}]*: {msg_val}')
                        led.off()
                        utime.sleep(0.1)
                    except RuntimeError as que:
                        print(f'{que}')

                wifi_client.disconnect()
            else:
                # if no connection - error
                light_signal(signal_wifi_reconect)
        # --- END TELEGRAM & NETWORK EXECUTION ---

        # --- MQTT EXECUTION ---
        if vars.MQTT_NEEDS_REPORT and utime.ticks_diff(
            utime.ticks_ms(), mqtt_last_time) >= vars.MQTT_UPDATES_TIMEOUT_MS:
            if wifi_client.reconnect(timeout=vars.WIFI_CONNECTION_TIMEOUT):
                
                mqtt_last_time = utime.ticks_ms()

                try:
                    # Searching for Home Assistant IP
                    if not ha_ip:
                        ha_ip = find_ha_ip()
                        print(f'[MQTT HA] Home Assistant actual IP: {ha_ip}')

                    light_signal(signal_ha_start_sending)
                    mqtt = MicroFenceMQTTRepresenter(
                        mqtt_user=vars.MQTT_USER,
                        mqtt_password=vars.MQTT_PASSWORD,
                        device_id=device_id,
                        server_ip=ha_ip,
                        devices_config=vars.MQTT_DEVICES,
                        on_ha_event=on_ha_event)

                    if not ha_init_disarmed:
                        ha_init_disarmed = mqtt.init_disarmed()
                    
                    mqtt.update_config()

                    # Executing queue 
                    while len(mqtt_queue) > 0:
                        try:
                            msg_type, msg_val = mqtt_queue.pop(0)

                            led.on()
                            if msg_type == Skyfall.MSG_FILE:
                                dev_id = int(msg_val.rsplit("_", 1)[1][:-4])
                                mqtt.update_image_state(device_id=dev_id, file_name=msg_val)
                            elif msg_type == Skyfall.MSG_TEXT:
                                dev_id = int(msg_val.split("Node ID ", 1)[1].split(" sent:", 1)[0])
                                msg = msg_val.split("sent: '", 1)[1].rsplit("'", 1)[0]
                                mqtt.event_motion_detected(device_id=dev_id, message=msg)
                            led.off()
                            utime.sleep(0.1)
                        except RuntimeError as mque:
                            print(f'{mque}')

                    # read ARM/DISARM from Home Assistant
                    mqtt.check_messages()

                except Exception as mqe:
                    print("[MQTT HA] error:", [mqe])
                    pass

                if mqtt: mqtt.disconnect()
                light_signal(signal_ha_end_sending)

                wifi_client.disconnect()
            else:
                light_signal(signal_wifi_reconect)
        # --- END MQTT EXECUTION ---
    except RuntimeError as ex:
        print(ex)
