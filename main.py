#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import math
import argparse
import pygame
import tiledtmxloader

from avatar import Avatar, Hero, create_hero_avatar
from world import World
from common import *

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

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

    # init pygame and set up a screen
    pygame.init()
    pygame.display.set_caption("tiledtmxloader - " + file_name + " - keys: arrows, 0-9")
    screen_width_px = 1024
    screen_height_px = 768
    screen = pygame.display.set_mode((screen_width_px, screen_height_px), pygame.DOUBLEBUF, 32)

    world = World(tiledtmxloader.tmxreader.TileMapParser().parse_decode(file_name))

    # create hero sprite
    # use floats for hero position
    hero_pos_x_px = screen_width_px
    hero_pos_y_px = screen_height_px
    hero = create_hero_avatar(hero_pos_x_px, hero_pos_y_px, 'ch_01_00.png')
    world.add_avatar(hero)

    # cam_offset is for scrolling
    cam_world_pos_x_px = hero.rect.centerx
    cam_world_pos_y_px = hero.rect.centery

    # set initial cam position and size
    world.renderer.set_camera_position_and_size(cam_world_pos_x_px, cam_world_pos_y_px, screen_width_px, screen_height_px)

    # add the hero the the right layer, it can be changed using 0-9 keys
    hero.add_to_sprite_layer(world.get_avatar_layer(hero.layer).sprite_layer)

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

        # find directions
        direction_x = pygame.key.get_pressed()[pygame.K_RIGHT] - pygame.key.get_pressed()[pygame.K_LEFT]
        direction_y = pygame.key.get_pressed()[pygame.K_DOWN] - pygame.key.get_pressed()[pygame.K_UP]

        # make sure the hero moves with same speed in all directions (diagonal!)
        dir_len = math.hypot(direction_x, direction_y)
        dir_len = dir_len if dir_len else 1.0

        # update position
        speed_x = 0.075 * 2.
        step_x_px = speed_x * dt * direction_x / dir_len
        speed_y = 0.053 * 2.
        step_y_px = speed_y * dt * direction_y / dir_len
        hero.try_to_move(world, dt, step_x_px, step_y_px)

        # adjust camera according to the hero's position
        world.set_camera_layer_level(hero.layer)
        world.set_camera_position(hero.rect.centerx, hero.rect.centery, hero.z)

        # clear screen, might be left out if every pixel is redrawn anyway
        screen.fill((0, 0, 0))

        # render the map
        for sprite_layer in world.all_sprite_layers:
            if sprite_layer.is_object_group:
                # we dont draw the object group layers
                # you should filter them out if not needed
                continue
            else:
                world.renderer.render_layer(screen, sprite_layer)


        world.draw_avatar_boxes(screen)

        pygame.display.flip()

#  -----------------------------------------------------------------------------

if __name__ == '__main__':
    main()
