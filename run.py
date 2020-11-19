from pyfactorio.render import transform
from pyfactorio.render import point
from pyfactorio.render.features import Feature, Features
import pygame
import time
import numpy as np
from pygame import surfarray

from pyfactorio.env.controller import FactorioController

from timeit import default_timer as timer

pygame.init()

w = 1000
h = 800

display = pygame.display.set_mode((w, h))

img = np.zeros((w, h, 3), dtype=np.uint8)


ctrlr = FactorioController()
ctrlr.start_game()
dims, (ow, oh), scale = ctrlr.zoom()

init_time = timer()
frames_displayed = 0

feature_dims = point.Point(480, 360)

world_to_camera = transform.Linear(scale=scale, offset=(ow,oh))
camera_to_feature = transform.Linear(scale=feature_dims/dims)

chain = transform.Chain(
    world_to_camera,
    camera_to_feature,
    transform.PixelToCoord()
)

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    obs = ctrlr.observe()
    fobs = Features.unpack_obs(obs, point.Point(ow, oh))
    print(fobs)

    # arr = np.array([type=np.float)

    surfarray.blit_array(display, img)
    pygame.display.flip()

    frames_displayed += 1

    interval = 1 / 30.0 - time.monotonic() % 1 / 30.0
    time.sleep(interval)
