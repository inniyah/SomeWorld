#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import math
import argparse
import pygame
import tiledtmxloader

from avatar import Avatar, Hero

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

HPIXELS_PER_METER = 32
VPIXELS_PER_METER = 23 # 45 degrees, so 32 * sqrt(2) / 2

# This class escapes a string, by replacing control characters by their hexadecimal equivalents
class escape(str): # pylint: disable=invalid-name
    def __repr__(self):
        return ''.join('\\x{:02x}'.format(ord(ch)) if ord(ch) < 32 else ch for ch in self)
    __str__ = __repr__

class JSONDebugEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, bytes):
            return escape(obj.decode('utf-8'))
        if isinstance(obj, tiledtmxloader.tmxreader.Tile):
            return 'Tile: id={} gid={} images={} properties={}'.format(obj.id, obj.gid, obj.images, obj.properties)
        if isinstance(obj, object):
            try:
                return [
                    ['%s' % (c,) for c in type.mro(type(obj))],
                    obj.__dict__,
                ]
            except AttributeError:
                return ['%s' % (c,) for c in type.mro(type(obj))]
        try:
            ret = json.JSONEncoder.default(self, obj)
        except:
            ret = ('%s' % (obj,))
        return ret

#  -----------------------------------------------------------------------------

def create_hero(start_pos_x, start_pos_y, path=None):
    """
    Creates the hero sprite.
    """
    if not path is None:
        hero = Hero(start_pos_x, start_pos_y, path)
        return hero

    else:
        image = pygame.Surface((25, 45), pygame.SRCALPHA)
        image.fill((255, 0, 0, 200))
        rect = image.get_rect()
        rect.midbottom = (start_pos_x, start_pos_y)
        return tiledtmxloader.helperspygame.SpriteLayer.Sprite(image, rect)


#  -----------------------------------------------------------------------------

def main():
    """
    Main method.
    """
    parser = argparse.ArgumentParser(description='World Demo')
    parser.add_argument('-v', '--verbose', action="store_true", help="verbose output" )
    args = parser.parse_args()

    if args.verbose:
        print("~ Verbose!")
    else:
        print("~ Not so verbose")

    path_to_map = os.path.join(os.path.dirname(__file__), 'data', 'maps', 'world.tmx')
    demo_pygame(path_to_map)

#  -----------------------------------------------------------------------------

def demo_pygame(file_name):
    """
    Example showing how to use the paralax scrolling feature.
    """

    # parser the map (it is done here to initialize the
    # window the same size as the map if it is small enough)
    world_map = tiledtmxloader.tmxreader.TileMapParser().parse_decode(file_name)

    #with open('debug_map.json', 'w') as f:
    #    json.dump(world_map, f, cls=JSONDebugEncoder, indent=2, sort_keys=True)

    # init pygame and set up a screen
    pygame.init()
    pygame.display.set_caption("tiledtmxloader - " + file_name + " - keys: arrows, 0-9")
    screen_width = min(1024, world_map.pixel_width)
    screen_height = min(768, world_map.pixel_height)
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF, 32)

    # load the images using pygame
    resources = tiledtmxloader.helperspygame.ResourceLoaderPygame()
    resources.load(world_map)

    # prepare map rendering
    assert world_map.orientation == "orthogonal"

    # renderer
    renderer = tiledtmxloader.helperspygame.RendererPygame()

    # create hero sprite
    # use floats for hero position
    hero_pos_x = screen_width
    hero_pos_y = screen_height
    hero = create_hero(hero_pos_x, hero_pos_y, 'data/avatars/ch_01_00.png')

    # cam_offset is for scrolling
    cam_world_pos_x = hero.rect.centerx
    cam_world_pos_y = hero.rect.centery

    # set initial cam position and size
    renderer.set_camera_position_and_size(cam_world_pos_x, cam_world_pos_y, screen_width, screen_height)

    # retrieve the layers
    sprite_layers = tiledtmxloader.helperspygame.get_layers_from_map(resources)

    # filter layers
    sprite_layers = [layer for layer in sprite_layers if not layer.is_object_group]

    # add the hero the the right layer, it can be changed using 0-9 keys
    sprite_layers[2].add_sprite(hero)

    # layer add/remove hero keys
    num_keys = [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, \
                    pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]

    # variables for the main loop
    clock = pygame.time.Clock()
    running = True
    # set up timer for fps printing
    pygame.time.set_timer(pygame.USEREVENT, 1000)

    # mainloop
    while running:
        dt = clock.tick()

        # event handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.USEREVENT:
                print("fps: ", clock.get_fps())
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in num_keys:
                    # find out which layer to manipulate
                    idx = num_keys.index(event.key)
                    # make sure this layer exists
                    if idx < len(world_map.layers):
                        if sprite_layers[idx].contains_sprite(hero):
                            sprite_layers[idx].remove_sprite(hero)
                            print("removed hero sprite from layer", idx)
                        else:
                            sprite_layers[idx].add_sprite(hero)
                            print("added hero sprite to layer", idx)
                    else:
                        print("no such layer or more than 10 layers: " + str(idx))

        # find directions
        direction_x = pygame.key.get_pressed()[pygame.K_RIGHT] - pygame.key.get_pressed()[pygame.K_LEFT]
        direction_y = pygame.key.get_pressed()[pygame.K_DOWN] - pygame.key.get_pressed()[pygame.K_UP]

        # make sure the hero moves with same speed in all directions (diagonal!)
        dir_len = math.hypot(direction_x, direction_y)
        dir_len = dir_len if dir_len else 1.0

        # update position
        speed_x = 0.075 * 2.
        step_x = speed_x * dt * direction_x / dir_len
        speed_y = 0.053 * 2.
        step_y = speed_y * dt * direction_y / dir_len
        hero_width = hero.rect.width
        hero_height = 5
        step_x, step_y = check_collision(hero.pos_x, hero.pos_y, step_x, step_y, hero_width, hero_height, world_map, sprite_layers[hero.layer])
        hero.move(dt, step_x, step_y)

        # adjust camera according to the hero's position, follow him
        # (don't make the hero follow the cam, maybe later you want different
        #  objects to be followd by the cam)
        renderer.set_camera_position(hero.rect.centerx, hero.rect.centery)

        # clear screen, might be left out if every pixel is redrawn anyway
        screen.fill((0, 0, 0))

        # render the map
        for sprite_layer in sprite_layers:
            if sprite_layer.is_object_group:
                # we dont draw the object group layers
                # you should filter them out if not needed
                continue
            else:
                renderer.render_layer(screen, sprite_layer)

        pygame.display.flip()

#  -----------------------------------------------------------------------------

# unused in this demo, just here to show how you could check for collision!
def is_walkable(pos_x, pos_y, coll_layer):
    """
    Just checks if a position in world coordinates is walkable.
    """
    tile_x = int(pos_x // coll_layer.tilewidth)
    tile_y = int(pos_y // coll_layer.tileheight)

    if coll_layer.content2D[tile_y][tile_x] is None:
        return True
    return False

#  -----------------------------------------------------------------------------

def special_round(value):
    """
    For negative numbers it returns the value floored,
    for positive numbers it returns the value ceiled.
    """
    if value < 0:
        return math.floor(value)
    return math.ceil(value)

#  -----------------------------------------------------------------------------

def is_walkable(pos_x, pos_y, world_map, coll_layer):
    """
    Just checks if a position in world coordinates is walkable.
    """
    tile_x = int(pos_x // coll_layer.tilewidth)
    tile_y = int(pos_y // coll_layer.tileheight)
    this_sprite = coll_layer.content2D[tile_y][tile_x]
    if this_sprite is not None:
        this_tile = world_map.tiles[this_sprite.key[0]]
        if this_tile.properties.get('block', None):
            return False
    return True

#  -----------------------------------------------------------------------------

def check_collision(hero_pos_x, hero_pos_y, step_x, step_y, hero_width, hero_height, world_map, coll_layer):
    """
    Checks collision of the hero against the world. Its not the best way to
    handle collision detection but for this demo it is good enough.

    :Returns: steps to add to heros current position.
    """
    # create hero rect
    hero_rect = pygame.Rect(0, 0, hero_width, hero_height)
    hero_rect.midbottom = (hero_pos_x, hero_pos_y)

    # find the tile location of the hero
    tile_x = int((hero_pos_x) // coll_layer.tilewidth)
    tile_y = int((hero_pos_y) // coll_layer.tileheight)

    # find the tiles around the hero and extract their rects for collision
    tile_rects = []
    for diry in (-1, 0 , 1):
        for dirx in (-1, 0, 1):
            this_sprite = coll_layer.content2D[tile_y + diry][tile_x + dirx]
            if this_sprite is not None:
                this_tiles = [world_map.tiles[k] for k in this_sprite.key]
                if this_tiles[0].properties.get('block', None):
                    #json.dump(this_tile.properties, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
                    tile_rects.append(this_sprite.rect)

    # save the original steps and return them if not canceled
    res_step_x = step_x
    res_step_y = step_y

    # x direction, floor or ceil depending on the sign of the step
    step_x = special_round(step_x)

    # detect a collision and dont move in x direction if colliding
    if hero_rect.move(step_x, 0).collidelist(tile_rects) > -1:
        res_step_x = 0

    # y direction, floor or ceil depending on the sign of the step
    step_y = special_round(step_y)

    # detect a collision and dont move in y direction if colliding
    if hero_rect.move(0, step_y).collidelist(tile_rects) > -1:
        res_step_y = 0

    # return the step the hero should do
    return res_step_x, res_step_y

#  -----------------------------------------------------------------------------

if __name__ == '__main__':
    main()
