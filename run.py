import pygame
import numpy as np
from pygame import surfarray

from pyfactorio.env.controller import FactorioController

from timeit import default_timer as timer

pygame.init()

w = 1000
h = 800

display = pygame.display.set_mode((w, h))

img = np.zeros((w,h,3),dtype=np.uint8)


ctrlr = FactorioController()
ctrlr.start_game()

init_time = timer()
frames_displayed = 0

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # updating the image
    for i in range(100):
        img[np.random.randint(w),np.random.randint(h)] = np.random.randint(255,size=3,dtype=np.uint8)

    surfarray.blit_array(display, img)
    pygame.display.flip()

    frames_displayed+=1