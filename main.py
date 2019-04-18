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
from world import World
from common import *

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

HPIXELS_PER_METER = 32
VPIXELS_PER_METER = 23 # 45 degrees, so 32 * sqrt(2) / 2

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

    world = World(tiledtmxloader.tmxreader.TileMapParser().parse_decode(file_name))

    #with open('debug_map.json', 'w') as f:
    #    json.dump(world.map, f, cls=JSONDebugEncoder, indent=2, sort_keys=True)

    # init pygame and set up a screen
    pygame.init()
    pygame.display.set_caption("tiledtmxloader - " + file_name + " - keys: arrows, 0-9")
    screen_width = min(1024, world.map.pixel_width)
    screen_height = min(768, world.map.pixel_height)
    screen = pygame.display.set_mode((screen_width, screen_height), pygame.DOUBLEBUF, 32)

    # create hero sprite
    # use floats for hero position
    hero_pos_x = screen_width
    hero_pos_y = screen_height
    hero = create_hero(hero_pos_x, hero_pos_y, 'data/avatars/ch_01_00.png')

    # cam_offset is for scrolling
    cam_world_pos_x = hero.rect.centerx
    cam_world_pos_y = hero.rect.centery

    # set initial cam position and size
    world.renderer.set_camera_position_and_size(cam_world_pos_x, cam_world_pos_y, screen_width, screen_height)

    # add the hero the the right layer, it can be changed using 0-9 keys
    world.sprite_layers[2].add_sprite(hero)

    # layer add/remove hero keys
    num_keys = [pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]

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
                    if idx < len(world.map.layers):
                        if world.sprite_layers[idx].contains_sprite(hero):
                            world.sprite_layers[idx].remove_sprite(hero)
                            print("removed hero sprite from layer", idx)
                        else:
                            world.sprite_layers[idx].add_sprite(hero)
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
        step_x, step_y = world.check_collision(hero.pos_x, hero.pos_y, step_x, step_y, hero_width, hero_height, world.sprite_layers[hero.layer])
        hero.move(dt, step_x, step_y)

        # adjust camera according to the hero's position, follow him
        # (don't make the hero follow the cam, maybe later you want different
        #  objects to be followd by the cam)
        world.renderer.set_camera_position(hero.rect.centerx, hero.rect.centery)

        # clear screen, might be left out if every pixel is redrawn anyway
        screen.fill((0, 0, 0))

        # render the map
        for sprite_layer in world.sprite_layers:
            if sprite_layer.is_object_group:
                # we dont draw the object group layers
                # you should filter them out if not needed
                continue
            else:
                world.renderer.render_layer(screen, sprite_layer)

        pygame.display.flip()

#  -----------------------------------------------------------------------------

if __name__ == '__main__':
    main()
