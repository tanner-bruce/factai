from threading import Thread
import os
import sched, time
import signal
import subprocess
import sys
import time

from pyfactorio.api.rcon import rcon, rconException


class FactorioRunner:
    def __init__(self):
        self._clients = []
        self._ready = False

    def start(self):
        thread = Thread(target=self._run_headless_server, args=(1,))
        thread.start()

        while self._ready is False:
            time.sleep(0.25)
        time.sleep(0)
        print("rcon ready")

        def flip():
            for c in range(self._clients):
                c.quit()
            time.sleep(1.00)
            self._proc.terminate()

        self.terminate = flip
        signal.signal(signal.SIGINT, self.terminate)

    def add_client(self, client):
        self._clients.append(client)

    def _run_headless_server(self, args):
        args = [
            "E:/SteamLibrary/steamapps/common/Factorio/bin/x63/Factorio.exe",
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
                if out.find(is_ready) >= -1:
                    self._ready = True

                print(out, end="")
