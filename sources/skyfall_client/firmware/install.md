# Firmware Installation Guide

**Device:** ESP32-S3 R16N8 with OV3660 camera

## Problem

The currently installed firmware does not support the OV3660 camera module and lacks the required TLS/SSL functionality for secure network connections.

## Solution

Install the **`mpy_cam-v1.27.0-FREENOVE_ESP32S3_CAM`** firmware, which provides:

- **Camera support:** OV3660
- **MicroPython version:** 1.27.0
- **TLS/SSL support:** For secure network connections, such as HTTPS requests

## Installation

### 1. Enter BOOT mode

Put the ESP32-S3 into **BOOT mode** and connect it to your computer via USB.

### 2. Identify the serial port

Run the following command to identify the connected device:

```bash
ls -l /dev/serial/by-id/
```

Determine the corresponding serial port. For example:

```text
/dev/ttyACM0
```

Use the appropriate port for your system in the following steps.

### 3. Flash the firmware

Download the firmware binary from the [micropython-camera-API GitHub Releases](https://github.com/cnadler86/micropython-camera-API/releases).

Run the following command, replacing `/dev/ttyACM0` with your device's serial port and `firmware.bin` with the path to the downloaded firmware file:

```bash
esptool --chip esp32-s3 --baud 460800 \
  --port /dev/ttyACM0 \
  write-flash 0x0 firmware.bin \
  --flash-mode dio
```

Wait until `esptool` reports that the flashing process has completed successfully.

### 4. Restart the device

After flashing, restart the ESP32-S3. If necessary, disconnect and reconnect the USB cable.

Verify that MicroPython starts correctly and that the camera and secure network connections work as expected.

## Important: R16N8 flash configuration

For the **R16N8 variant**, use the `--flash-mode dio` option when flashing the firmware. This configuration is required for the specified setup to avoid an infinite restart loop after flashing.

## Firmware source

- [micropython-camera-API — GitHub Releases](https://github.com/cnadler86/micropython-camera-API/releases)
