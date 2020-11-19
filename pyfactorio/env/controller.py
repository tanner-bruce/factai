import logging
import subprocess
import time
from threading import Thread

from pyfactorio.util import get_desktop_size
from pyfactorio.api.rcon import rcon


class FactorioController:
    def __init__(self, addr="127.0.0.1", password="pass", port=9889):
        self._addr = addr
        self._password = password
        self._port = port
        self._ready = False
        self._rcon = None
        self._proc = None

    def quit(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc = None
        if self._rcon is not None:
            self._rcon.disconnect()
            self._rcon = None

    def restart(self):
        self._proc.terminate()
        self.start_game()

    def zoom(self, zoom=0.7):
        self._do_zoom(zoom)
        return zoom

    def _do_zoom(self, zoom):
        display_info = self._rcon.command("/zoom %f" % zoom)
        self._zoom = zoom
        self._desktop_size = get_desktop_size()
        self._width = display_info[0][b"width"]  # type: ignore
        self._height = display_info[0][b"height"]  # type: ignore
        self._tiles_w = (60.0 * self._width) / (self._zoom * self._desktop_size.x)  # type: ignore
        # TODO TB - this isn't right but it's close
        self._tiles_h = (32.0 * self._height) / (self._zoom * self._desktop_size.y)  # type: ignore

    def act(self, actions):
        return ()

    def step(self, step=1):
        return self._rcon.command("/step %d" % step)

    def observe(self, count=1):
        return self._rcon.command("/observe %d" % count)

    def game_info(self):
        return ()

    def start_game(self):
        self._thread = Thread(target=self._start_process)
        self._thread.start()

        while self._ready is False:
            time.sleep(0.25)
        time.sleep(0.5)
        print("connecting to rcon")
        self._rcon = rcon(self._addr, self._password, self._port)
        self._rcon.connect()
        self._rcon.command("/h", unpack=False)
        print("rcon connected")
        print("setting zoom")
        # set a default starting zoom
        self.zoom()
        print("zoom set")

    def _start_process(self):
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
            out = ""
            output = self._proc.stdout.readline()
            if output == b"" and process.poll() is not None:
                break
            if output:
                out = output.decode()
                is_ready = "joined the game"
                if out.find(is_ready) >= -1:
                    self._ready = True

            print(out, end="")
