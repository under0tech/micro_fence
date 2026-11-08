# installation

```bash
ls -l /dev/serial/by-id/

esptool --port /dev/ttyACM0 erase_flash

esptool --port /dev/ttyACM0 --baud 460800 write_flash 0 ESP32_GENERIC_C3-20260824-v1.29.0.bin
```
