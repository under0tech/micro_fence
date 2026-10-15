import neopixel

import definitions as vars

from machine import Pin, PWM, ADC, Timer, deepsleep
from radio import RadioHC12
from skyfall import Skyfall
from cam2640 import make_photo
from utime import sleep

# -------------------------
# Configuration
# -------------------------
pir = Pin(vars.PIR_PIN, Pin.IN)
button = Pin(vars.BUTTON_PIN, Pin.IN, Pin.PULL_UP)
led = neopixel.NeoPixel(Pin(vars.BUTTON_LED_PIN), 1)
ledm = neopixel.NeoPixel(Pin(vars.MUSIC_LED_PIN), 1)
buzzer = PWM(Pin(vars.BUZZER_PIN))
adc = ADC(Pin(vars.ADC_PIN), atten=ADC.ATTN_11DB)

def ledm_on():
    ledm[0] = (0, 0, 255)
    ledm.write()

def ledm_off():
    ledm[0] = (0, 0, 0)
    ledm.write()

def pir_irq(pin):
    global pir_detected
    pir_detected = True

def pir_detection():
    print("Motion detected")
    if secured:
        print("WARNING!!!!")
        play_melody(melody_warning)

        photo_file = 'photo_ov2640.jpg'
        if make_photo(filename=photo_file):
            sleep(1)
            protocol.broadcast_secured_file(
                vars.RADIO_SERVER_ID,
                photo_file)
            
        sleep(2)

def button_irq(pin):
    global btn_clicked
    btn_clicked = True

def button_click():
    global secured
    print("Button pressed")
    secured = not secured

    if secured:
        led[0] = (255, 0, 0)
        print("SECURE ON")
        play_melody(melody_alarm_on)
    else:
        led[0] = (0, 0, 0)
        print("SECURE OFF")
        play_melody(melody_alarm_off)
    led.write()

# -------------------------
# Radio HC-12
# -------------------------
client_radio = RadioHC12(uart_id=vars.RADIO_UART_ID, 
                        tx=vars.RADIO_TX, rx=vars.RADIO_RX, 
                        baudrate=vars.RADIO_BAUDRATE, 
                        my_id=vars.RADIO_MY_ID, 
                        allowed_devices=vars.RADIO_ALLOWED_DEVICES)

protocol = Skyfall(radio_instance=client_radio, 
                   encryption_keys=vars.CLIENT_KEYS)

def protocol_receiver_callback(msg_type, value):
    global secured

    print(f'[RadiO] we have receieved: {msg_type}: {value}')

    if msg_type == Skyfall.MSG_TEXT:
        if 'Arm' in value:
            secured = False
            button_click()
        elif 'Disarm' in value:
            secured = True
            button_click()

# -------------------------
# Buzzer
# -------------------------
melody_start = [
    (523, 0.12),   # C5
    (659, 0.12),   # E5
    (784, 0.16),   # G5
    (1047, 0.35),  # C6
]

melody_alarm_on = [
    (180, 0.30),  # F#3
    (180, 0.15),  # F#3
    (220, 0.25),  # A3
    (180, 0.15),  # F#3
    (330, 0.18),  # E4
    (220, 0.25),  # A3
]

melody_alarm_off = [
    (1760, 0.25),  # A6
    (1320, 0.15),  # E6
    (880, 0.12),   # A5
    (660, 0.40),   # E5
]

melody_warning = [
    (850, 0.50),  # G#5
]

melody_alarm = [
    (1500, 4.0),  # F#6
]

melody_shutdown = [
    (1760, 0.18),  # A6
    (1480, 0.18),  # F#6
    (1320, 0.20),  # E6
    (1100, 0.22),  # C#6
    (880,  0.28),  # A5
    (660,  0.45),  # E5
    (440,  0.65),  # A4
]

def play_tone(freq, duration):
    ledm_on()
    buzzer.freq(freq)
    buzzer.duty_u16(vars.BUZZER_VOLUME)
    sleep(duration)
    buzzer.duty_u16(0)
    ledm_off()
    sleep(0.03)

def play_melody(melody):
    buzzer.init()
    for note, duration in melody:
        play_tone(note, duration)
    buzzer.deinit()
    ledm_off()

# -------------------------
# Battery
# -------------------------
def battery_check(timer):
    global need_shutdown

    divider_ratio = (470 + 100) / 100 #5.7

    raw = adc.read_u16()
    voltage = raw * 3.4 * divider_ratio / 65535

    print(f"RAW: {raw:5d}  VSYS: {voltage:.2f} V")

    if voltage < vars.LOW_BATTERY:
        print("Low battery")
        need_shutdown = True

# -------------------------
# Shutdown
# -------------------------
def shutdown():
    print('>shutdown!')

    pir.irq(handler=None)
    button.irq(handler=None)
    led[0] = (0, 0, 0)
    led.write()

    timer.deinit()
    timer = None
    
    play_melody(melody_shutdown)
    ledm_on()
    sleep(2)
    ledm_off()
    sleep(1)
    deepsleep()

# -------------------------
# Init
# -------------------------
secured = False
btn_clicked = False
pir_detected = False
need_shutdown = False

pir.irq(trigger=Pin.IRQ_RISING,
        handler=pir_irq)

button.irq(trigger=Pin.IRQ_FALLING,
        handler=button_irq)

timer = Timer(0)
timer.init(
    period=1 * 60 * 1000, # 60 sec
    mode=Timer.PERIODIC,
    callback=battery_check)

# -------------------------
# Main loop
# -------------------------
play_melody(melody_start)

while True:
    print('...')
    if pir_detected:
        sleep(0.5)
        pir_detection()
        pir_detected = False
    if btn_clicked:
        sleep(0.5)
        button_click()
        btn_clicked = False
    if need_shutdown:
        shutdown()

    try:
        if client_radio.uart.any() != 0:
            protocol.read_secured_packages(
                    on_message=protocol_receiver_callback,
                    uart_timeout=vars.RADIO_UART_TIMEOUT_MS)
    except: pass

    sleep(0.5)