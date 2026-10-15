import definitions as vars

from utime import sleep
from radio import RadioHC12
from skyfall import Skyfall
from machine import Pin, PWM, ADC, deepsleep

# -------------------------
# Configuration
# -------------------------
led = Pin(vars.BUTTON_LED_PIN, Pin.OUT)
button = Pin(vars.BUTTON_PIN, Pin.IN, Pin.PULL_UP)
pir = Pin(vars.PIR_PIN, Pin.IN)
ledm = Pin(vars.MUSIC_LED_PIN, Pin.OUT)
buzzer = PWM(Pin(vars.BUZZER_PIN))
battery_adc = ADC(Pin(vars.ADC_PIN))

def button_irq(pin):
    global btn_clicked
    btn_clicked = True

def pir_irq(pin):
    global pir_detected
    pir_detected = True

def pir_detection():
    print("Motion detected")
    if secured:
        print("WARNING!!!!")
        play_melody(melody_warning)

        protocol.broadcast_secured_message(
                    vars.RADIO_SERVER_ID,
                    f"Motion detected on PIR west.")

        sleep(2)

def button_click():
    global secured
    print("Button pressed")
    secured = not secured

    if secured:
        led.on()
        print("SECURE ON")
        play_melody(melody_alarm_on)
    else:
        led.off()
        print("SECURE OFF")
        play_melody(melody_alarm_off)

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
    ledm.on()
    buzzer.freq(freq)
    buzzer.duty_u16(vars.BUZZER_VOLUME)
    sleep(duration)
    buzzer.duty_u16(0)
    ledm.off()
    sleep(0.03)

def play_melody(melody):
    buzzer.init()
    for note, duration in melody:
        play_tone(note, duration)
    buzzer.deinit()
    ledm.off()

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
# Battery
# -------------------------
def battery_check():
    global need_shutdown
    global battery_voltage

    raw = battery_adc.read_u16()
    voltage = raw * 5.9 * 3.2 / 65535

    battery_voltage = voltage
    adc_str = f"Voltage: {voltage:.2f}v"
    print(adc_str)

    if voltage < vars.LOW_BATTERY:
        print("Low battery")
        need_shutdown = True

    return adc_str

# -------------------------
# Shutdown
# -------------------------
def shutdown():
    print('>shutdown!')
    led.on()
    play_melody(melody_shutdown)
    led.off()
    sleep(1)
    deepsleep()

# -------------------------
# Init
# -------------------------
led.off()
ledm.off()

secured = False
btn_clicked = False
pir_detected = False
need_shutdown = False

button.irq(trigger=Pin.IRQ_FALLING,
        handler=button_irq)

pir.irq(trigger=Pin.IRQ_RISING,
        handler=pir_irq)

# -------------------------
# Main loop
# -------------------------
play_melody(melody_start)

while True:
    print('...')
    led.off()
    ledm.off()

    battery_check()
    if need_shutdown:
        shutdown()

    if btn_clicked:
        sleep(0.5)
        button_click()
        btn_clicked = False
    if pir_detected:
        sleep(0.2)
        pir_detection()
        pir_detected = False

    try:
        if client_radio.uart.any() != 0:
            protocol.read_secured_packages(
                    on_message=protocol_receiver_callback,
                    uart_timeout=vars.RADIO_UART_TIMEOUT_MS)
    except: pass

    sleep(0.5)

