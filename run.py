from pyfactorio.render.game import ActionCmd
from pyfactorio.render import transform
from pyfactorio.render import point
from pyfactorio.render import game
from pyfactorio.render.features import Feature, Features
import pygame
import time
import numpy as np
from pygame import surfarray
import signal

from pyfactorio.env.controller import FactorioController

from timeit import default_timer as timer


ctrlr = FactorioController()
ctrlr.start_game()
di = ctrlr.zoom()

init_time = timer()
feature_dims = di.camera_world_space_dims


g = game.RendererHuman()
g.init(None, di)
# g.init_window(di=di)



running = True
def qu(a, b):
    global running
    running = False
    g.close()
signal.signal(signal.SIGINT, qu)

while running:
    # for event in pygame.event.get():
    #     if event.type == pygame.QUIT:
    #         running = False
    obs = ctrlr.observe()
    fobs = Features.unpack_obs(obs)
    # print(fobs)

    g.render(fobs)

    act = g.get_actions(ctrlr)
    if act == ActionCmd.QUIT:
        running = False

    # player_pos = point.Point(fobs[1], fobs[2])


    # # (78.5, 33.5) -> (0, 0)
    # normalize_to_origin = transform.Linear(offset=player_pos-di.camera_tl_player_offset_dims)

    # # 0 - 114
    # # -> 
    # # 0 - width_of_surface
    # camera_to_feature = transform.Linear(scale=di.screen_dims/di.camera_world_space_dims)


    # chain = transform.Chain(
    #     normalize_to_origin,
    #     camera_to_feature,
    #     transform.PixelToCoord()
    # )


    # arr = np.array([type=np.float)

    # surfarray.blit_array(display, img) pygame.display.flip()

    interval = 1 / 60.0 - time.monotonic() % 1 / 60.0
