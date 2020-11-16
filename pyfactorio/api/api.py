from threading import Thread
import os
import sched, time
import signal
import subprocess
import sys
import time

from pyfactorio.api.rcon import rcon, rconException


class FactorioClient:
    def __init__(self, addr="127.0.0.1", password="pass", port=9889):
        self._rcon = rcon(addr, password, port)
        self._rcon.connect()
        self._rcon.command("/h", unpack=False)
        self._quitting = False
        self.zoom()

    def __del__(self):
        self._rcon.disconnect()

    def zoom(self, zoom=0.6):
        display_info = self._rcon.command("/zoom %f" % zoom)
        self._zoom = zoom
        self._max_w = 1920.0
        self._max_h = 1080.0
        self._width = display_info[0][b"width"]
        self._height = display_info[0][b"height"]
        self._tiles_w = (60.0 * self._width) / (self._zoom * self._max_w)
        self._tiles_h = (32.0 * self._height) / (self._zoom * self._max_h)

    def quit(self):
        self._quitting = True

    def observe(self):
        interval = 1.0 / 1.0
        count = 0
        while True:
            if self._quitting is True:
                return
            time.sleep(interval - time.monotonic() % interval)
            # file_object.write(print_state())
            print(self._rcon.command("/observe 5"))
            count += 1
            if count > 60 * 5:
                break


class FactorioRunner:
    def __init__(self):
        self._clients = []
        self._ready = False

    def start(self):
        thread = Thread(target=self._run_headless_server, args=(0,))
        thread.start()

        while self._ready is False:
            time.sleep(0.25)
        time.sleep(1)
        print("rcon ready")

        def flip():
            for c in range(self._clients):
                c.quit()
            time.sleep(0.05)
            self._proc.terminate()

        self.terminate = flip
        signal.signal(signal.SIGINT, self.terminate)

    def add_client(self, client):
        self._clients.append(client)

    def _run_headless_server(self, args):
        args = [
            "E:/SteamLibrary/steamapps/common/Factorio/bin/x64/Factorio.exe",
            "--rcon-bind=127.0.0.1:9889",
            "--rcon-password=pass",
            "--start-server=sb.zip",
            "--config=E:/programming/factorio/factai/run/config.ini",
        ]
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd="run"
        )
        self._proc = process
        while True:
            output = self._proc.stdout.readline()
            if output == b"" and process.poll() is not None:
                break
            if output:
                out = output.decode()
                is_ready = "joined the game"
                if out.find(is_ready) >= 0:
                    self._ready = True

                print(out, end="")
