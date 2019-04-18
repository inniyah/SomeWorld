#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tiledtmxloader
import sys
import os
import math
import glob
import re
import pygame
import vectors

def special_round(value):
    """
    For negative numbers it returns the value floored,
    for positive numbers it returns the value ceiled.
    """
    if value < 0:
        return math.floor(value)
    return math.ceil(value)

class World():
    def __init__(self, map):
        self.map = map

        # load the images using pygame
        self.resources = tiledtmxloader.helperspygame.ResourceLoaderPygame()
        self.resources.load(self.map)

        # prepare map rendering
        assert self.map.orientation == "orthogonal"

        # renderer
        self.renderer = tiledtmxloader.helperspygame.RendererPygame()

        # retrieve the layers
        self.sprite_layers = tiledtmxloader.helperspygame.get_layers_from_map(self.resources)

        # filter layers
        self.sprite_layers = [layer for layer in self.sprite_layers if not layer.is_object_group]

    def is_walkable(self, pos_x, pos_y, coll_layer):
        """
        Just checks if a position in world coordinates is walkable.
        """
        tile_x = int(pos_x // coll_layer.tilewidth)
        tile_y = int(pos_y // coll_layer.tileheight)
        this_sprite = coll_layer.content2D[tile_y][tile_x]
        if this_sprite is not None:
            this_tile = self.map.tiles[this_sprite.key[0]]
            if this_tile.properties.get('block', None):
                return False
        return True

    def check_collision(self, hero_pos_x, hero_pos_y, step_x, step_y, hero_width, hero_height, coll_layer):
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
                    this_tiles = [self.map.tiles[k] for k in this_sprite.key]
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
