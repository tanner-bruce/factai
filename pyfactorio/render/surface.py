import pygame
from pyfactorio.render import transform, point, stopwatch
from pyfactorio.env.controller import DisplayInfo


sw = stopwatch.sw


class Surface(object):
    """A surface to display on screen."""

    def __init__(
        self, surf, surf_type, surf_rect, world_to_surf, di: DisplayInfo, draw
    ):
        """A surface to display on screen.

        Args:
          surf: The actual pygame.Surface (or subsurface).
          surf_type: A SurfType, used to tell how to treat clicks in that area.
          surf_rect: Rect of the surface relative to the window.
          world_to_surf: Convert a world point to a pixel on the surface.
          draw: A function that draws onto the surface.
        """
        self.surf = surf
        self.surf_type = surf_type
        self.surf_rect = surf_rect
        self.world_to_surf = None
        self.translate = None
        self.player_to_surf = world_to_surf
        self.draw = draw
        self.origin: point.Point = None
        self.di = di

    def set_pos(self, pos: point.Point):
        self.origin = pos
        self.translate = transform.Linear(
            offset=self.di.camera_tl_player_offset_dims - pos
        )
        self.world_to_surf = transform.Chain(self.translate, self.player_to_surf)

    def draw_line(self, color, start_loc, end_loc, thickness: int = 1):
        """Draw a line using world coordinates and thickness."""
        pygame.draw.line(
            self.surf,
            color,
            self.world_to_surf.fwd_pt(start_loc).round(),
            self.world_to_surf.fwd_pt(end_loc).round(),
            max(1, thickness),
        )

    def draw_arc(
        self, color, world_loc, world_radius, start_angle, stop_angle, thickness=1
    ):
        """Draw an arc using world coordinates, radius, start and stop angles."""
        center = self.world_to_surf.fwd_pt(world_loc).round()
        radius = max(1, int(self.world_to_surf.fwd_dist(world_radius)))
        rect = pygame.Rect(center - radius, (radius * 2, radius * 2))
        pygame.draw.arc(
            self.surf,
            color,
            rect,
            start_angle,
            stop_angle,
            thickness if thickness < radius else 0,
        )

    def draw_circle(self, color, world_loc, world_radius, thickness=0):
        """Draw a circle using world coordinates and radius."""
        if world_radius > 0:
            center = self.world_to_surf.fwd_pt(world_loc).round()
            radius = max(1, int(self.world_to_surf.fwd_dist(world_radius)))
            pygame.draw.circle(
                self.surf, color, center, radius, thickness if thickness < radius else 0
            )

    def draw_rect_pts(self, color, tl, br, thickness=0):
        """Draw a rectangle using world coordinates."""
        tl = self.world_to_surf.fwd_pt(tl).round()
        br = self.world_to_surf.fwd_pt(br).round()
        rect = pygame.Rect(tl, br - tl)
        pygame.draw.rect(self.surf, color, rect, thickness)

    def draw_rect(self, color, world_rect, thickness=0):
        """Draw a rectangle using world coordinates."""
        self.draw_rect_pts(color, world_rect.tl, world_rect.br, thickness)

    def blit_np_array(self, array):
        """Fill this surface using the contents of a numpy array."""
        with sw("make_surface"):
            raw_surface = pygame.surfarray.make_surface(array.transpose([1, 0, 2]))
        with sw("draw"):
            pygame.transform.scale(raw_surface, self.surf.get_size(), self.surf)

    def write_screen(self, font, color, screen_pos, text, align="left", valign="top"):
        """Write to the screen in font.size relative coordinates."""
        pos = point.Point(*screen_pos) * point.Point(0.75, 1) * font.get_linesize()
        text_surf = font.render(str(text), True, color)
        rect = text_surf.get_rect()
        if pos.x >= 0:
            setattr(rect, align, pos.x)
        else:
            setattr(rect, align, self.surf.get_width() + pos.x)
        if pos.y >= 0:
            setattr(rect, valign, pos.y)
        else:
            setattr(rect, valign, self.surf.get_height() + pos.y)
        self.surf.blit(text_surf, rect)

    def write_world(self, font, color, world_loc, text):
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect()
        rect.center = self.world_to_surf.fwd_pt(world_loc)
        self.surf.blit(text_surf, rect)


def circle_mask(shape, pt, radius):
    # ogrid is confusing but seems to be the best way to generate a circle mask.
    # http://docs.scipy.org/doc/numpy/reference/generated/numpy.ogrid.html
    # http://stackoverflow.com/questions/8647024/how-to-apply-a-disc-shaped-mask-to-a-numpy-array
    y, x = np.ogrid[-pt.y : shape.y - pt.y, -pt.x : shape.x - pt.x]
    # <= is important as radius will often come in as 0 due to rounding.
    return x ** 2 + y ** 2 <= radius ** 2