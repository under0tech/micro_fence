
import os
import json
import socket
import ssl

import urequests as rq

class TelegaWc:
    """
    Telegram Bot API client
    for ESP32-C3 microcontrollers.

    Provides communication with Telegram.
    Supports sending text messages and files,
    as well as retrieving updates from a channel.
    """

    def __init__(
            self,
            telegram_host,
            telegram_bot_id,
            telegram_chat_id):
        """
        Initialize the Telegram client.

        :param telegram_host:
            Telegram Bot API server hostname.

        :param telegram_bot_id:
            Telegram bot API bot identifier used for API requests.

        :param telegram_chat_id:
            Telegram chat or channel ID used as the destination
            for outgoing messages.
        """

        self.telegram_host = telegram_host
        self.telegram_bot_id = telegram_bot_id
        self.telegram_chat_id = telegram_chat_id

    def _url_encode(self, text):
        """
        Encodes text for use in a URL.

        :param text:
            Text to encode.

        :return:
            URL-encoded text.
        """

        return text.replace("%", "%25").replace(" ", "%20").replace(":", "%3A")

    def send_message(self, message) -> bool:
        """
        Send a text message through the Telegram Bot API.

        Creates an HTTP POST request for the Telegram sendMessage 
        endpoint, and sends the message.

        :param message:
            Text message to send to the Telegram chat.

        :return:
            True if the message was successfully transmitted.
            False if the data transmission fails.
        """
        
        text = self._url_encode(message)
        try:
            res = rq.post(
                    f'https://{self.telegram_host}/{self.telegram_bot_id}/sendMessage?chat_id={self.telegram_chat_id}&parse_mode=Markdown&text={text}')
            if res.status_code == 200:
                print(f'[TELEGAWC] successfully sent: {message}')
                return True
            else:
                print('[TELEGAWC] error: ', [res.status_code])
        except Exception as e:
            print(f'[TELEGAWC] problem sending message: ', [e])
            return False

        return False

    def send_photo(self, filename, caption=""):
        """
        Send a photo to Telegram.

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

        boundary = "----esp32c37MA4YWxk"
        chunk_size = 2048
        sock = None

        try:
            name = filename.rsplit("/", 1)[-1]
            filesize = os.stat(filename)[6]

            if name.lower().endswith(".png"):
                mime = "image/png"
            elif name.lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            else:
                mime = "application/octet-stream"

            chat_part = (
                "--{}\r\n"
                'Content-Disposition: form-data; name="chat_id"\r\n'
                "\r\n"
                "{}\r\n"
            ).format(boundary, self.telegram_chat_id).encode()

            caption_part = b""

            if caption:
                caption_part = (
                    "--{}\r\n"
                    'Content-Disposition: form-data; name="caption"\r\n'
                    "\r\n"
                    "{}\r\n"
                ).format(boundary, caption).encode()

            file_part = (
                "--{}\r\n"
                'Content-Disposition: form-data; name="photo"; filename="{}"\r\n'
                "Content-Type: {}\r\n"
                "\r\n"
            ).format(boundary, name, mime).encode()

            ending = "\r\n--{}--\r\n".format(boundary).encode()

            content_length = (
                len(chat_part) +
                len(caption_part) +
                len(file_part) +
                filesize +
                len(ending)
            )

            path = "/{}/sendPhoto".format(self.telegram_bot_id)

            request = (
                "POST {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Type: multipart/form-data; boundary={}\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n"
                "\r\n").format(
                            path,
                            self.telegram_host,
                            boundary,
                            content_length).encode()

            print("[TELEGAWC] sending:", name, "-", filesize, "bytes")

            addr = socket.getaddrinfo(
                self.telegram_host,
                443,
                socket.AF_INET,
                socket.SOCK_STREAM)[0][-1]

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect(addr)

            sock = ssl.wrap_socket(
                sock,
                server_hostname=self.telegram_host)

            def send(data):
                while data:
                    count = sock.send(data)
                    if count is None or count <= 0:
                        return False
                    data = data[count:]
                return True

            if not send(request):
                return False

            if not send(chat_part):
                return False

            if caption_part and not send(caption_part):
                return False

            if not send(file_part):
                return False

            with open(filename, "rb") as f:
                sent = 0

                while True:
                    chunk = f.read(chunk_size)

                    if not chunk:
                        break

                    if not send(chunk):
                        print("[TELEGAWC] photo upload failed at", sent, "bytes")
                        return False

                    sent += len(chunk)

            if not send(ending):
                return False

            response = sock.recv(1024)

            if b"200 OK" not in response:
                print("[TELEGAWC] error:", response)
                return False

            print("[TELEGAWC] photo sent:", name)
            return True

        except OSError as e:
            print("[TELEGAWC] photo error:", e)
            return False

        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass

    def get_updates(self, offset=0):
        """
        Retrieve the latest channel post from the Telegram Bot API.

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

        sock = None

        try:
            params = "allowed_updates=%5B%22channel_post%22%5D"

            if offset:
                params += "&offset={}".format(offset)

            path = "/{}/getUpdates?{}".format(
                self.telegram_bot_id,
                params)

            print("[TELEGAWC] getting updates:", path)

            request = (
                "GET {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Connection: close\r\n"
                "\r\n").format(path,
                        self.telegram_host).encode()

            addr = socket.getaddrinfo(
                self.telegram_host,
                443,
                socket.AF_INET,
                socket.SOCK_STREAM)[0][-1]

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            sock.settimeout(30)
            sock.connect(addr)

            sock = ssl.wrap_socket(
                sock,
                server_hostname=self.telegram_host)

            sent = 0

            while sent < len(request):
                n = sock.send(request[sent:])

                if n is None or n <= 0:
                    return None

                sent += n

            # Receive response
            response = b""

            while True:
                chunk = sock.recv(1024)

                if not chunk:
                    break

                response += chunk

            if not response.startswith(b"HTTP/1.1 200"):
                print("[TELEGAWC] HTTP error:", response[:100])
                return None

            separator = response.find(b"\r\n\r\n")

            if separator < 0:
                return None

            body = response[separator + 4:]

            data = json.loads(body)

            if not data.get("ok"):
                print("[TELEGAWC] getting updates - error:", data)
                return None

            updates = data.get("result", [])

            if not updates:
                return None

            last_update = updates[-1]

            update_id = last_update.get("update_id")
            channel_post = last_update.get("channel_post")

            if update_id is None or not channel_post:
                return None

            sender_chat = channel_post.get("sender_chat")

            if not sender_chat:
                return None

            chat_id = sender_chat.get("id")
            text = channel_post.get("text")

            if chat_id is None or text is None:
                return None

            print(
                "[TELEGAWC] got update:",
                chat_id,
                update_id,
                "-",
                text)

            return chat_id, update_id, text

        except Exception as e:
            print("[TELEGAWC] getting updates - error:", e)
            return None

        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass