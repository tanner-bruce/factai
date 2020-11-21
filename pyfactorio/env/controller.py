from collections import namedtuple
from threading import Thread
import subprocess
import time

from pyfactorio.api.rcon import rcon
from pyfactorio.render import point

DisplayInfo = namedtuple(
    "DisplayInfo",
    [
        "screen_dims",
        "camera_tl_player_offset_dims",
        "camera_world_space_dims",
    ],
)


class FactorioController:
    def __init__(self, addr: str="127.0.0.1", password: str="pass", port: int=9889):
        self._addr: str = addr
        self._password: str = password
        self._port: int = port
        self._ready: bool = False
        self._rcon: rcon = None
        self._proc = None
        self._thread: Thread = None
        self._quitting: bool = False

    def quit(self) -> None:
        self._quitting = True
        self._thread.join(timeout=5)
        if self._proc is not None:
            self._proc.terminate()
            self._proc = None
        if self._rcon is not None:
            self._rcon.disconnect()
            self._rcon = None

    def restart(self) -> None:
        self._proc.terminate()
        self.start_game()

    def zoom(self, zoom: float = 0.7) -> DisplayInfo:
        return self._do_zoom(zoom)

    def _do_zoom(self, zoom: float) -> DisplayInfo:
        display_info = self._rcon.command("/zoom %f" % zoom)
        self._zoom = zoom
        print(display_info)
        self._display_size = point.Point(display_info[0][b"width"], display_info[0][b"height"])  # type: ignore
        self._camera_dim_offset = point.Point(display_info[1][0], display_info[1][1])  # type: ignore
        self._camera_dims = self._camera_dim_offset * 2  # type: ignore
        # self._screen_scale = self._tiles_dims / self._camera_dims
        self._di = DisplayInfo(
            screen_dims=self._camera_dims,
            # screen_scale=self._screen_scale,
            camera_tl_player_offset_dims=self._camera_dim_offset,
            camera_world_space_dims=self._camera_dim_offset * 2,
        )
        return self._di

    def display_info(self) -> DisplayInfo:
        return self._di

    def act(self, actions):
        return ()

    def step(self, step: int=1) -> str:
        return self._rcon.command("/step %d" % step)

    def observe(self, count: int=1) -> str:
        return self._rcon.command("/observe %d" % count)

    def start_game(self) -> None:
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

    def _start_process(self) -> None:
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
        while self._quitting is False:
            out = ""
            output = self._proc.stdout.readline()
            if output == b"" and process.poll() is not None:
                break
            if output:
                out = output.decode()
                is_ready = "joined the game"
                if out.find(is_ready) >= 0:
                    self._ready = True

            print(out, end="")
