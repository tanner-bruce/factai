from pyfactorio.render import memoize
from pyfactorio.render import point
import re
import platform
import pygame

import subprocess

@memoize.memoize
def get_desktop_size():
    """Get the desktop size."""
    if platform.system() == "Linux":
        try:
            xrandr_query = subprocess.check_output(["xrandr", "--query"])
            sizes = re.findall(r"\bconnected primary (\d+)x(\d+)", str(xrandr_query))
            if sizes[0]:
                return point.Point(int(sizes[0][0]), int(sizes[0][1]))
        except:  # pylint: disable=bare-except
            print("Failed to get the resolution from xrandr.")

    # Most general, but doesn't understand multiple monitors.
    display_info = pygame.display.Info()
    return point.Point(display_info.current_w, display_info.current_h)
