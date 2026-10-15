# Type: Thunderball
# Role: PIR sensor with No camera
# Communications: HC-12 radio client
# Microcontroller: RPi Pico
# Peripheral: PIR sensor HC-SR501, button with LED, 
#             buzzer, ADC

### GPIO CONFIGURATION
BUTTON_PIN = 14
BUTTON_LED_PIN = 12
PIR_PIN = 3
MUSIC_LED_PIN = 17
BUZZER_PIN = 2
BUZZER_VOLUME = 5000 # volume (0-65535)

ADC_PIN = 28
LOW_BATTERY = 3.5 # 3.5V

### RADIO HC-12
CLIENT_KEYS = {
    1: b"e8edcbad-9ec0-4686-aca0-d4d884222757"
}
RADIO_SERVER_ID = 1
RADIO_BAUDRATE = 9600
RADIO_UART_ID = 1
RADIO_TX = 4
RADIO_RX = 5
RADIO_UART_TIMEOUT_MS = 2000
RADIO_MY_ID = 3 # client, "PIR sensor with No camera" (Thunderball)
RADIO_ALLOWED_DEVICES = [1] #ServerId = 1, our radio group