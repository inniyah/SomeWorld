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
from common import *

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

        #with open('debug_map.json', 'w') as f:
        #    json.dump(self.map, f, cls=JSONDebugEncoder, indent=2, sort_keys=True)

        # renderer
        self.renderer = tiledtmxloader.helperspygame.RendererPygame()

        self.avatar_layers = {}
        self.metadata_layers = {}

        self.all_sprite_layers = []
        for idx, layer in enumerate(self.resources.world_map.layers):
            if not layer.is_object_group:
                print("Layer '{}' ({}): {}".format(layer.name, 'visible' if layer.visible else 'not visible', layer.properties))
                sprite_layer = tiledtmxloader.helperspygame.get_layer_at_index(idx, self.resources)
                self.all_sprite_layers.append(sprite_layer)

                if layer.properties.get('Metadata', None):
                    self.metadata_layers[int(layer.properties.get('Level', 0))] = (layer, sprite_layer)
                if layer.properties.get('Avatar', None):
                    self.avatar_layers[int(layer.properties.get('Level', 0))] = (layer, sprite_layer)

        print("Avatar Layers: {}".format(self.avatar_layers))
        print("Metadata Layers: {}".format(self.metadata_layers))

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
                    this_tiles = [self.map.tiles.get(k, None) for k in this_sprite.key if k in self.map.tiles]
                    if this_tiles and this_tiles[0].properties.get('Block', None) in ['true']:
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
