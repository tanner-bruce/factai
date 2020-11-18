from pyfactorio.api.rcon import rcon, rconException
from pyfactorio.render.game import get_desktop_size


class FactorioController:
    def __init__(self, addr="127.0.0.1", password="pass", port=9889):
        self._rcon = rcon(addr, password, port)
        self._rcon.connect()
        self._rcon.command("/h", unpack=False)
        self._quitting = False

        # set a default starting zoom
        self.zoom()

    def __del__(self):
        self._rcon.disconnect()

    def zoom(self, zoom=0.7):
        display_info = self._rcon.command("/zoom %f" % zoom)
        self._zoom = zoom
        # TODO TB - get desktop resolution
        self._desktop_size = get_desktop_size()
        self._width = display_info[0][b"width"]
        self._height = display_info[0][b"height"]
        self._tiles_w = (60.0 * self._width) / (self._zoom * self._desktop_size.x)
        # TODO TB - this isn't right but it's close
        self._tiles_h = (32.0 * self._height) / (self._zoom * self._desktop_size.y)
        return zoom

    def act(self, actions):
        # perform actions
        return

    def observe(self):
        return self._rcon.command("/observe 5")

    def game_info(self):
        return ()