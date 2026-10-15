import utime

from machine import UART


class WiFi:
    """
    Wi-Fi driver for microcontrollers using an ESP8285 AT-command module.

    Provides Wi-Fi network management and SSL/TCP communication
    through a UART-connected ESP module using AT commands.
    """

    def __init__(
            self,
            uart_id=0,
            baudrate=115200):
        """
        Initialize the Wi-Fi driver.

        :param uart_id:
            UART peripheral number used to communicate with
            the ESP AT-command module. Default is 0.

        :param baudrate:
            UART communication speed in bits per second.
            Default is 115200.
        """

        self.uart = UART(uart_id, baudrate)

    def _send_at_command(
            self,
            cmd_bytes,
            success_target=b'OK',
            timeout_secs=5):

        """
        Send an AT command and wait for the expected response.

        Reads data from the UART buffer until the success target,
        an error response, or the timeout is reached.

        :param cmd_bytes:
            AT command to send to the ESP module as bytes.

        :param success_target:
            Byte sequence that indicates successful command execution.
            Default is b'OK'.

        :param timeout_secs:
            Maximum time to wait for a response in seconds.
            Default is 5 seconds.

        :return:
            True if the success target is received.
            False if an error, failure, or timeout occurs.
        """

        self.uart.write(cmd_bytes)

        response = b''
        start_time = utime.time()

        while (utime.time() - start_time) < timeout_secs:

            if self.uart.any():

                data = self.uart.read()

                if data is not None:
                    response += data

                if success_target in response:
                    print(
                        "Success:",
                        response.decode('utf-8')
                    )
                    return True

                if b'ERROR' in response or b'FAIL' in response:
                    print(
                        "Failed:",
                        response.decode('utf-8')
                    )
                    return False

            utime.sleep_ms(50)

        print(
            "Timeout: Partial response:",
            response.decode('utf-8')
        )

        return False

    def _is_connected(self):
        """
        Check whether the ESP8285 Wi-Fi module is currently connected
        to a Wi-Fi access point.

        :return:
            True if the module reports an active Wi-Fi connection.
            False if no connection is reported or the request times out.
        """

        self.uart.write(b'AT+CWJAP?\r\n')

        response = b''
        start = utime.ticks_ms()

        while utime.ticks_diff(
                utime.ticks_ms(), start) < 3000:

            if self.uart.any():

                data = self.uart.read()

                if data:
                    response += data

                    if b'+CWJAP:' in response:
                        return True

                    if b'No AP' in response or b'ERROR' in response:
                        return False

            utime.sleep_ms(50)

        return False

    def connect(self, hostname, network, password):
        """
        Configure the ESP8285 Wi-Fi module and connect to a Wi-Fi network.

        Sets the module to Station mode, configures its hostname,
        connects to the specified access point, and retrieves
        the assigned local IP address.

        :param hostname:
            Hostname to assign to the ESP Wi-Fi module.

        :param network:
            Wi-Fi network name (SSID).

        :param password:
            Wi-Fi network password.

        :return:
            True if all configuration and connection steps succeed.
            False if any AT command fails or times out.
        """

        # 1. Set Wi-Fi mode to Station
        if not self._send_at_command(
                b'AT+CWMODE=1\r\n'):
            return False

        # 2. Set hostname
        hostname_cmd = (
            b'AT+CWHOSTNAME="' +
            hostname.encode('utf-8') +
            b'"\r\n'
        )

        if not self._send_at_command(hostname_cmd):
            return False

        # 3. Connect to Access Point
        jap_cmd = (
            b'AT+CWJAP="' +
            network.encode('utf-8') +
            b'","' +
            password.encode('utf-8') +
            b'"\r\n'
        )

        if not self._send_at_command(
                jap_cmd,
                success_target=b'WIFI CONNECTED',
                timeout_secs=15):
            return False

        # 4. Get local IP address
        if not self._send_at_command(
                b'AT+CIFSR\r\n',
                timeout_secs=10):
            return False

        print("Wi-Fi successfully connected!")

        return True

    def reconnect(self, network, password):
        """
        Check the current Wi-Fi connection and reconnect if necessary.

        If the ESP module is already connected to an access point,
        no reconnection is attempted.

        :param network:
            Wi-Fi network name (SSID).

        :param password:
            Wi-Fi network password.

        :return:
            True if already connected or reconnection succeeds.
            False if the connection attempt fails or times out.
        """

        if self._is_connected():
            return True

        return self._send_at_command(
            b'AT+CWJAP="' +
            network.encode() +
            b'","' +
            password.encode() +
            b'"\r\n',
            success_target=b'WIFI CONNECTED',
            timeout_secs=15
        )

    def establish_ssl(self, url):
        """
        Establish an SSL connection to a remote server.

        Uses the ESP AT command interface to create an SSL
        connection on TCP port 443.

        :param url:
            Remote server hostname or address to connect to.

        :return:
            True if the SSL connection is established.
            False if an error, failure, or timeout occurs.
        """

        cmd = b'AT+CIPSTART="SSL","' + url.encode() + b'",443\r\n'

        self.uart.write(cmd)

        response = b''
        start = utime.ticks_ms()

        while utime.ticks_diff(utime.ticks_ms(), start) < 15000:

            if self.uart.any():
                data = self.uart.read()

                if data:
                    response += data
                    print(data.decode('utf-8'))

                    if b'CONNECT' in response:
                        return True

                    if b'ERROR' in response or b'FAIL' in response:
                        return False

            utime.sleep_ms(50)

        return False

    def send_ssl_data(self, data):
        """
        Send raw data through the established SSL connection.

        First requests permission from the ESP module to send the
        specified number of bytes, then writes the data to UART
        and waits for the SEND OK response.

        :param data:
            Data to send through the SSL connection as bytes.

        :return:
            True if the data is sent successfully.
            False if the send operation fails or times out.
        """

        if not data:
            return True

        cmd = (
            b'AT+CIPSEND=' +
            str(len(data)).encode() +
            b'\r\n'
        )

        if not self._send_at_command(
                cmd,
                success_target=b'>',
                timeout_secs=5):
            return False

        self.uart.write(data)

        response = b''
        start = utime.ticks_ms()

        while utime.ticks_diff(
                utime.ticks_ms(), start) < 10000:

            if self.uart.any():

                resp = self.uart.read()

                if resp:
                    response += resp

                    if b'SEND OK' in response:
                        return True

                    if b'ERROR' in response or b'FAIL' in response:
                        print(response.decode('utf-8'))
                        return False

            utime.sleep_ms(20)

        print("SEND OK timeout")
        return False

    def get_ssl_data(self, request, timeout_secs=15):
        """
        Send a request through the SSL connection and wait for
        an HTTP response.

        The method waits until an HTTP response header is detected,
        then reads the remaining available UART data before returning
        the complete received response.

        :param request:
            Request data to send through the SSL connection as bytes.

        :param timeout_secs:
            Maximum time to wait for an HTTP response in seconds.
            Default is 15 seconds.

        :return:
            Received HTTP response as bytes.
            None if the request fails or the response times out.
        """

        if not self._send_at_command(
                b'AT+CIPSEND=' +
                str(len(request)).encode() +
                b'\r\n',
                success_target=b'>',
                timeout_secs=5):
            return None

        self.uart.write(request)

        response = b''
        start = utime.ticks_ms()

        while utime.ticks_diff(
                utime.ticks_ms(), start) < timeout_secs * 1000:

            if self.uart.any():

                data = self.uart.read()

                if data:
                    response += data

                    if b'SEND OK' in response:
                        # Keep waiting for HTTP response
                        pass

                    if b'HTTP/1.1' in response:
                        # Give the ESP a little time to receive
                        # the complete HTTP response
                        utime.sleep_ms(1000)

                        while self.uart.any():
                            data = self.uart.read()
                            if data:
                                response += data

                        return response

                    if b'ERROR' in response or b'FAIL' in response:
                        print(response.decode('utf-8'))
                        return None

            utime.sleep_ms(50)

        print("HTTP response timeout")
        return None