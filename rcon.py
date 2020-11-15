import argparse
import getpass
import os
import socket
import ssl
import select
import struct
import time

from io import BytesIO

import msgpack

class rconException(Exception):
    pass


class rcon(object):
    """A client for handling Remote Commands (RCON) to a Minecraft server
    The recommend way to run this client is using the python 'with' statement.
    This ensures that the socket is correctly closed when you are done with it
    rather than being left open.
    Example:
    In [1]: from mcrcon import rcon
    In [2]: with rcon("10.1.1.1", "sekret") as mcr:
       ...:     resp = mcr.command("/whitelist add bob")
       ...:     print(resp)
    While you can use it without the 'with' statement, you have to connect
    manually, and ideally disconnect:
    In [3]: mcr = rcon("10.1.1.1", "sekret")
    In [4]: mcr.connect()
    In [5]: resp = mcr.command("/whitelist add bob")
    In [6]: print(resp)
    In [7]: mcr.disconnect()
    """

    socket = None

    def __init__(self, host, password, port=9889, tlsmode=0):
        self.host = host
        self.password = password
        self.port = port
        self.tlsmode = tlsmode

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, tb):
        self.disconnect()

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Enable TLS
        if self.tlsmode > 0:
            ctx = ssl.create_default_context()

            # Disable hostname and certificate verification
            if self.tlsmode > 1:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            self.socket = ctx.wrap_socket(self.socket, server_hostname=self.host)

        self.socket.connect((self.host, self.port))
        self._send(3, self.password)

    def disconnect(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def _read(self, length):
        data = b""
        while len(data) < length:
            data += self.socket.recv(length - len(data))
        return data

    def _receive_all(self, unpack=False):
        if self.socket is None:
            raise rconException("Must connect before sending data")

        while True:
            # Read a packet
            in_data = b""
            (in_length,) = struct.unpack("<i", self._read(4))
            in_payload = self._read(in_length)
            in_id, in_type = struct.unpack("<ii", in_payload[:8])
            in_data_partial, in_padding = in_payload[8:-2], in_payload[-2:]

            if unpack:
                in_data_partial = in_data_partial[:-1]

            # Sanity checks
            if in_padding != b"\x00\x00":
                raise rconException("Incorrect padding")
            if in_id == -1:
                raise rconException("Login failed")

            # Record the response
            in_data += in_data_partial

            # If there's nothing more to receive, return the response
            if len(select.select([self.socket], [], [], 0)[0]) == 0:
                if unpack:
                    return msgpack.unpackb(in_data)
                return in_data


    def _send(self, out_type, out_data, unpack=False):
        if self.socket is None:
            raise rconException("Must connect before sending data")

        # Send a request packet
        out_payload = (
            struct.pack("<ii", 0, out_type) + out_data.encode("utf8") + b"\x00\x00"
        )
        out_length = struct.pack("<i", len(out_payload))
        self.socket.send(out_length + out_payload)

        return self._receive_all(unpack=unpack)


    def command(self, command):
        result = self._send(2, command, unpack=True)
        time.sleep(0.003)
        return result