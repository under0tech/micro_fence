# Firmware Installation Guide

**Model:** RP2040 Pico W with ESP8285 Wi-Fi module

## Problem

The ESP8285 Wi-Fi module included with the Pico W does not have TLS/SSL support in its default firmware. This prevents the device from making HTTPS requests, which are required for sending messages to Telegram.

## Solution

The ESP8285 firmware can be replaced with **ESP_ATMod.0.6.bin**, which provides TLS/SSL support.

### 1. Flash the Pico W with Serial Port Transmission firmware

First, put the Pico W into **BOOTSEL mode**.

Flash the Pico with:

`Serial_port_transmission.uf2`

Simply copy the `.uf2` file to the **RPI-RP2** drive that appears in the Linux file manager.

This firmware turns the Pico W into a serial port bridge, allowing communication with the ESP8285.

### 2. Flash the ESP8285 firmware

Connect the Pico W to the computer and determine which serial port it uses:

```bash
ls -l /dev/serial/by-id/
```

In this example, the port is:

`/dev/ttyACM0`

Use `esptool` to flash the new ESP8285 firmware:

```bash
esptool --port /dev/ttyACM0 write-flash 0x0 ESP_ATMod.0.6.bin
```

Wait for the flashing process to complete successfully.

### 3. Restore the standard Pico W firmware

After successfully updating the ESP8285, put the Pico W into **BOOTSEL mode** again.

Flash the standard Raspberry Pi Pico W MicroPython firmware:

`RPI_PICO_W-20231227-v1.22.0.uf2`

Copy the `.uf2` file to the **RPI-RP2** drive in the usual way.

The Pico W is now restored to its normal MicroPython firmware, while the ESP8285 retains the updated firmware with TLS/SSL support.

## Reference

The **ESP_ATMod.0.6.bin** firmware is available here:

https://github.com/JiriBilek/RP2040_PicoW_ESP8285_Library/blob/master/firmware/ESP_ATMod.0.6.bin