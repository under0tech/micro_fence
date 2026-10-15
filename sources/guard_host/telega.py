import os
import json

from wifi import WiFi


class Telegram:
    """
    Telegram Bot API client for microcontrollers.

    Provides communication with Telegram through a Wi-Fi client
    using HTTPS requests. Supports sending text messages and photos,
    as well as receiving channel updates.
    """

    def __init__(
            self,
            wifi_client: WiFi,
            telegram_host,
            telegram_bot_id,
            telegram_chat_id):
        """
        Initialize the Telegram client.

        :param wifi_client:
            Initialized Wi-Fi client used to establish SSL connections
            and transmit HTTP requests.

        :param telegram_host:
            Telegram Bot API server hostname.

        :param telegram_bot_id:
            Telegram bot API bot identifier used for API requests.

        :param telegram_chat_id:
            Telegram chat or channel ID used as the destination
            for outgoing messages and photos.
        """

        self.wifi_client = wifi_client
        self.telegram_host = telegram_host
        self.telegram_bot_id = telegram_bot_id
        self.telegram_chat_id = telegram_chat_id

    def send_message(self, message):
        """
        Send a text message through the Telegram Bot API.

        Establishes an SSL connection to the Telegram server,
        creates an HTTP POST request for the sendMessage endpoint,
        and sends the message using form-encoded data.

        :param message:
            Text message to send to the configured Telegram chat.

        :return:
            True if the message was successfully transmitted.
            False if the SSL connection or data transmission fails.
        """

        if self.wifi_client.establish_ssl(self.telegram_host):

            url = f'/{self.telegram_bot_id}/sendMessage'

            data = (
                'chat_id={}'
                '&parse_mode=Markdown'
                '&text={}'
            ).format(self.telegram_chat_id, message)

            request = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Type: application/x-www-form-urlencoded\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
                "{}"
            ).format(
                url,
                self.telegram_host,
                len(data),
                data
            ).encode('utf-8')

            if self.wifi_client.send_ssl_data(request):
                print(f'[TELEGA] successfully sent: {message}')
                return True

            print(f'[TELEGA] problem sending: {message}')

        return False


    def send_photo(self, filename, caption=""):
        """
        Send a photo file through the Telegram Bot API.

        Builds a multipart/form-data HTTP request and transfers
        the photo from local storage in chunks to reduce memory usage.

        The photo MIME type is determined from its file extension.
        PNG and JPEG images are supported explicitly; other file
        types are sent as application/octet-stream.

        :param filename:
            Path to the photo file stored on the microcontroller.

        :param caption:
            Optional text caption to send together with the photo.
            Default is an empty string.

        :return:
            True if the complete request is transmitted successfully.
            False if the file cannot be accessed, the SSL connection
            fails, or any part of the request cannot be sent.
        """

        try:

            boundary = "----PicoBoundary7MA4YWxk"
            chunk_size = 2048

            name = filename.split("/")[-1]
            filesize = os.stat(filename)[6]

            if name.lower().endswith(".png"):
                mime = "image/png"
            elif name.lower().endswith(".jpg"):
                mime = "image/jpeg"
            elif name.lower().endswith(".jpeg"):
                mime = "image/jpeg"
            else:
                mime = "application/octet-stream"

            chat_part = (
                "--{}\r\n"
                'Content-Disposition: form-data; name="chat_id"\r\n'
                "\r\n"
                "{}\r\n"
            ).format(
                boundary,
                self.telegram_chat_id
            ).encode()

            caption_part = b""

            if caption:
                caption_part = (
                    "--{}\r\n"
                    'Content-Disposition: form-data; name="caption"\r\n'
                    "\r\n"
                    "{}\r\n"
                ).format(
                    boundary,
                    caption
                ).encode()

            file_header = (
                "--{}\r\n"
                'Content-Disposition: form-data; name="photo"; filename="{}"\r\n'
                "Content-Type: {}\r\n"
                "\r\n"
            ).format(
                boundary,
                name,
                mime
            ).encode()

            ending = (
                "\r\n--{}--\r\n".format(boundary)
            ).encode()

            body_length = (
                len(chat_part) +
                len(caption_part) +
                len(file_header) +
                filesize +
                len(ending)
            )

            url = f'/{self.telegram_bot_id}/sendPhoto'

            http_header = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Type: multipart/form-data; boundary={}\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).format(
                url,
                self.telegram_host,
                boundary,
                body_length
            ).encode()

            print("File:", name)
            print("File size:", filesize)
            print("HTTP size:", len(http_header) + body_length)

            # Establish SSL connection
            if not self.wifi_client.establish_ssl(
                    self.telegram_host):
                return False

            # Send HTTP header
            if not self.wifi_client.send_ssl_data(
                    http_header):
                return False

            # Send chat_id
            if not self.wifi_client.send_ssl_data(
                    chat_part):
                return False

            # Send caption
            if caption_part:
                if not self.wifi_client.send_ssl_data(
                        caption_part):
                    return False

            # Send multipart file header
            if not self.wifi_client.send_ssl_data(
                    file_header):
                return False

            # Send photo data
            with open(filename, "rb") as f:

                sent = 0

                while True:

                    chunk = f.read(chunk_size)

                    if not chunk:
                        break

                    if not self.wifi_client.send_ssl_data(
                            chunk):
                        print("Failed at:", sent)
                        return False

                    sent += len(chunk)

                    print(
                        "Photo:",
                        sent,
                        "/",
                        filesize
                    )

            # Send multipart ending
            if not self.wifi_client.send_ssl_data(
                    ending):
                return False

            print("[TELEGA] photo successfully sent:", name)
            return True

        except OSError:
            print(f"Could not locate '{filename}' in storage.")

        return False


    def _extract_ipd_data(self, response):
        """
        Extract and concatenate payloads from ESP8285 +IPD responses.

        Searches the received UART data for +IPD frames and extracts
        the specified payload from each frame. Multiple payloads are
        concatenated into a single byte sequence.

        :param response:
            Raw response received from the ESP8285 AT interface.

        :return:
            Concatenated payload data as bytes.
            Returns an empty byte sequence if no valid +IPD payload
            is found.
        """

        data = bytearray()
        pos = 0

        while True:
            start = response.find(b'+IPD,', pos)

            if start < 0:
                break

            colon = response.find(b':', start)

            if colon < 0:
                break

            try:
                length = int(response[start + 5:colon])
            except ValueError:
                break

            payload_start = colon + 1
            payload_end = payload_start + length

            if payload_end > len(response):
                break

            data.extend(response[payload_start:payload_end])

            pos = payload_end

        return bytes(data)

    def get_updates(self, offset=0):
        """
        Retrieve the latest channel update from the Telegram Bot API.

        Establishes an SSL connection, requests channel_post updates,
        extracts the HTTP response from ESP8285 +IPD frames, parses
        the JSON response, and returns the latest valid channel post.

        :param offset:
            Identifier of the first update to retrieve.
            Updates with an ID lower than this value are ignored.
            Default is 0.

        :return:
            A tuple containing:
                - chat_id:
                    Telegram ID of the channel that sent the post.
                - update_id:
                    Unique Telegram update identifier.
                - text:
                    Text content of the channel post.

            Returns None if the connection fails, no updates are
            available, the response is invalid, or the update does
            not contain a valid channel post.
        """

        if not self.wifi_client.establish_ssl(self.telegram_host):
            return None

        params = 'allowed_updates=["channel_post"]'

        if offset != 0:
            params += f'&offset={offset}'

        url = f'/{self.telegram_bot_id}/getUpdates?{params}'

        print(f'[TELEGA] getting updates: /getUpdates?{params}\r\n')

        request = (
            "GET {} HTTP/1.1\r\n"
            "Host: {}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).format(url, self.telegram_host).encode()

        response = self.wifi_client.get_ssl_data(request)

        if not response:
            return None

        try:
            # Extract and concatenate all ESP8266 +IPD payloads
            response = self._extract_ipd_data(response)

            if not response:
                return None

            # Find HTTP body
            separator = response.find(b"\r\n\r\n")

            if separator < 0:
                return None

            body = response[separator + 4:].strip()

            # Get data from JSON
            data = json.loads(body)

            if not data.get("ok"):
                print("[TELEGA] getting updates - error:", data)
                return None

            updates = data.get("result", [])

            if not updates:
                return None

            last_update = updates[-1]
            update_id = last_update.get("update_id")
            channel_post = last_update.get("channel_post")

            if not channel_post:
                return None

            sender_chat = channel_post.get("sender_chat")

            if not sender_chat:
                return None

            chat_id = sender_chat.get("id")
            text = channel_post.get("text")

            if text is None or update_id is None:
                return None

            print(f"[TELEGA] got updates: {chat_id}, {update_id} - {text}")
            return chat_id, update_id, text

        except Exception as e:
            print("[TELEGA] getting updates - error:", e)

        return None


