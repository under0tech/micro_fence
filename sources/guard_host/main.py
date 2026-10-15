import os
import utime

import definitions as vars

from utime import sleep
from machine import Pin
from wifi import WiFi
from radio import RadioHC12
from skyfall import Skyfall
from telega import Telegram

# -------------------------
# Configuration
# -------------------------
led = Pin(vars.NETWORK_LED_PIN, Pin.OUT)

# -------------------------
# WiFi
# -------------------------
wifi_client = WiFi(uart_id=vars.WIFI_UART_ID, 
                   baudrate=vars.WIFI_UART_BAUDRATE)

# -------------------------
# Telega
# -------------------------
telegram_client = Telegram(wifi_client=wifi_client,
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
    telegram_queue.append((msg_type, value))

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

def light_led(value, duration):
    led.value(value)
    sleep(duration)
    sleep(0.03)

def light_signal(signal):
    for value, duration in signal:
        light_led(value, duration)

# -------------------------
# Init
# -------------------------
light_signal(signal_init)

light_signal(signal_wifi_connect)
wifi_client.connect(hostname=vars.WIFI_CLIENT_HOSTNAME, 
                    network=vars.WIFI_NETWORK_NAME, 
                    password=vars.WIFI_NETWORK_PASSWORD)
led.off()

# -------------------------
# Main loop
# -------------------------
offset = 0
telegram_queue = []
telegram_last_time = (utime.ticks_ms() - 
                      vars.TELEGRAM_UPDATES_TIMEOUT_MS)

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
        if utime.ticks_diff(
            utime.ticks_ms(), telegram_last_time) >= vars.TELEGRAM_UPDATES_TIMEOUT_MS:
            if wifi_client.reconnect(vars.WIFI_NETWORK_NAME, 
                                vars.WIFI_NETWORK_PASSWORD):           
                
                telegram_last_time = utime.ticks_ms()

                # Getting updates from Telegram and reaction
                try:
                    light_signal(signal_start_sending)
                    res = telegram_client.get_updates(offset=offset)
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
                            telegram_client.send_message(reply_text)
                            light_signal(signal_reply_end_sending)

                        if text == 'Arm' or text == 'Disarm':
                            for dst_id, key in vars.SERVER_KEYS.items():
                                light_signal(signal_reply_start_sending)
                                protocol.broadcast_secured_message(dst_id, text)
                                sleep(0.4)
                                light_signal(signal_reply_end_sending)
                except: pass

                # Executing queue 
                while len(telegram_queue) > 0:
                    try:
                        msg_type, msg_val = telegram_queue.pop(0)

                        led.on()
                        if msg_type == Skyfall.MSG_FILE:
                            telegram_client.send_photo(
                                            msg_val, 
                                            f'[File: {msg_val}]')
                            sleep(1)
                            if msg_val in os.listdir(): 
                                os.remove(msg_val)
                        elif msg_type == Skyfall.MSG_TEXT:
                            telegram_client.send_message(msg_val)
                        led.off()
                        sleep(0.1)
                    except RuntimeError as que:
                        print(f'{que}')
            else:
                # if no connection - error
                light_signal(signal_wifi_reconect)
        # --- END TELEGRAM & NETWORK EXECUTION ---
    except RuntimeError as ex:
        print(ex)

