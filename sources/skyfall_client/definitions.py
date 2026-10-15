# Type: Skyfall
# Role: PIR sensor with camera
# Microcontroller: ESP32S3 R16N8
# Communications: HC-12 radio client
# Peripheral: camera ov2640, button with LED, 
#             PIR sensor AM312, buzzer, ADC

### GPIO CONFIGURATION
PIR_PIN = 41
BUTTON_PIN = 14
BUTTON_LED_PIN = 47
MUSIC_LED_PIN = 48
BUZZER_PIN = 21
BUZZER_VOLUME = 5000 # volume (0-65535)
ADC_PIN = 1
LOW_BATTERY = 3.5 # 3.5V

### RADIO HC-12
CLIENT_KEYS = {
    1: b"6a7d6b5c-5814-83eb-983f-29b3dc953fde"
}
RADIO_SERVER_ID = 1
RADIO_BAUDRATE = 9600
RADIO_UART_ID = 1
RADIO_TX = 40
RADIO_RX = 39
RADIO_UART_TIMEOUT_MS = 2000
RADIO_MY_ID = 2 # client, "PIR sensor with camera" (Skyfall)
RADIO_ALLOWED_DEVICES = [1] #ServerId = 1, our radio group