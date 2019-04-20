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
from avatar import create_avatar

def special_round(value):
    """
    For negative numbers it returns the value floored,
    for positive numbers it returns the value ceiled.
    """
    if value < 0:
        return math.floor(value)
    return math.ceil(value)

class World():
    HPIXELS_PER_METER = 32.0
    VPIXELS_PER_METER = 23.0 # 45 degrees, so 32 * sqrt(2) / 2
    METERS_PER_LAYER = 2.0

    def __init__(self, map):
        self.map = map
        self.avatars = set()
        self.avatars_dict = {}
        self.camera_layer_level = None
        self.show_layer_level_up = False

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
            if layer.is_object_group:
                print("Objects Layer '{}' ({}): {}".format(layer.name, 'visible' if layer.visible else 'not visible', layer.properties))
                #json.dump(layer, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
                for obj in layer.objects:
                    obj_id = obj.properties.get('Id', None)
                    obj_type = obj.properties.get('Type', None)
                    layer_level = int(layer.properties.get('Level', 0))
                    if obj_type == 'avatar':
                        print("Avatar '{}' ('{}') at x={}, y={}".format(obj_id, obj_type, obj.x, obj.y))
                        create_avatar(self, layer_level, obj.x, obj.y, obj_id, obj.properties)
                    else:
                        print("Object '{}' ('{}') at x={}, y={}".format(obj_id, obj_type, obj.x, obj.y))
            else:
                print("Tiled Layer '{}' ({}): {}".format(layer.name, 'visible' if layer.visible else 'not visible', layer.properties))
                sprite_layer = tiledtmxloader.helperspygame.get_layer_at_index(idx, self.resources)
                self.all_sprite_layers.append(sprite_layer)

                if layer.properties.get('Metadata', None):
                    self.metadata_layers[int(layer.properties.get('Level', 0))] = (layer, sprite_layer)
                if layer.properties.get('Avatar', None):
                    self.avatar_layers[int(layer.properties.get('Level', 0))] = (layer, sprite_layer)

        print("Avatar Layers: {}".format(self.avatar_layers))
        print("Metadata Layers: {}".format(self.metadata_layers))

    def adjust_layer_level_visibility(self):
        show_layer_level = self.camera_layer_level
        if self.show_layer_level_up:
            show_layer_level += 1
        for idx, layer in enumerate(self.resources.world_map.layers):
            if not layer.is_object_group:
                layer_level = int(layer.properties.get('Level', 0))
                is_metadata = layer.properties.get('Metadata', None)
                sprite_layer = self.all_sprite_layers[idx]
                if layer_level <= show_layer_level and not is_metadata:
                    sprite_layer.visible = True
                else:
                    sprite_layer.visible = False

    def set_camera_layer_level(self, new_layer_level):
        if new_layer_level == self.camera_layer_level:
            return
        self.camera_layer_level = new_layer_level
        self.adjust_layer_level_visibility()

    def set_camera_position(self, pos_x, pos_y, pos_z):
        self.renderer.set_camera_position(pos_x, pos_y)
        if not self.show_layer_level_up and pos_z >= 1.5:
            self.show_layer_level_up = True
            self.adjust_layer_level_visibility()
        elif self.show_layer_level_up and pos_z < 1.0:
            self.show_layer_level_up = False
            self.adjust_layer_level_visibility()

    def get_pos_info(self, pos_x, pos_y, metadata_layer):
        tile_x = int(pos_x // metadata_layer.tilewidth)
        tile_y = int(pos_y // metadata_layer.tileheight)
        this_sprite = metadata_layer.content2D[tile_y][tile_x]
        this_tiles = None
        if this_sprite is not None:
            this_tiles = [self.map.tiles.get(k, None) for k in this_sprite.key if k in self.map.tiles]
        return tile_x, tile_y, this_sprite, this_tiles

    def is_walkable(self, pos_x, pos_y, metadata_layer):
        """
        Just checks if a position in world coordinates is walkable.
        """
        tile_x = int(pos_x // metadata_layer.tilewidth)
        tile_y = int(pos_y // metadata_layer.tileheight)
        this_sprite = metadata_layer.content2D[tile_y][tile_x]
        if this_sprite is not None:
            this_tile = self.map.tiles[this_sprite.key[0]]
            if this_tile.properties.get('block', None):
                return False
        return True

    def check_collision(self, hero_pos_x, hero_pos_y, step_x, step_y, hero_width, hero_height, metadata_layer):
        """
        Checks collision of the hero against the world. Its not the best way to
        handle collision detection but for this demo it is good enough.

        :Returns: steps to add to heros current position.
        """
        # create hero rect
        hero_rect = pygame.Rect(0, 0, hero_width, hero_height)
        hero_rect.midbottom = (hero_pos_x, hero_pos_y)

        # find the tile location of the hero
        tile_x = int((hero_pos_x) // metadata_layer.tilewidth)
        tile_y = int((hero_pos_y) // metadata_layer.tileheight)

        # find the tiles around the hero and extract their rects for collision
        tile_rects = []
        for diry in (-1, 0 , 1):
            for dirx in (-1, 0, 1):
                this_sprite = metadata_layer.content2D[tile_y + diry][tile_x + dirx]
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

    def add_avatar(self, avatar):
        self.avatars.add(avatar)
        if avatar.id:
            self.avatars_dict[avatar.id] = avatar

    # pygame.draw.lines(screen, color, closed, pointlist, thickness)
    # pygame.draw.rect(screen, color, (x,y,width,height), thickness)
    # pygame.draw.circle(screen, color, (x,y), radius, thickness)
    # pygame.draw.arc(screen, color, (x,y,width,height), start_angle, stop_angle, thickness)

    def draw_avatar_boxes(self, screen):
        color_red = (255,0,0)
        color_green = (0,255,0)
        color_blue = (0,0,255)
        color_white = (255,255,255)
        color_black = (0,0,0)

        for avatar in self.avatars:
            avatar_layer = self.avatar_layers[avatar.layer][1]

            #pos_x, pos_y = avatar.get_map_pos()

            metadata_layer = self.metadata_layers[avatar.layer][1]
            #pos_x, pos_y, tile_x, tile_y, sprite, tiles = avatar.get_map_pos_info(self, metadata_layer)
            pos_x, pos_y, tile_x, tile_y, tile_avg_height, tile_x_slope, tile_y_slope, sprite, tiles = avatar.get_map_pos_height_info(self, metadata_layer)

            mx = (pos_x // avatar_layer.tilewidth) * metadata_layer.tilewidth
            my = (pos_y // avatar_layer.tileheight) * metadata_layer.tileheight
            mx, my = self.renderer.world_to_screen(avatar_layer, mx, my)
            pygame.draw.rect(screen, color_blue, [mx, my,  metadata_layer.tilewidth, metadata_layer.tileheight], 2)

            if not tile_avg_height is None:
                h_avg = metadata_layer.tileheight * tile_avg_height
                h_dx = (metadata_layer.tileheight * tile_x_slope) / 2.0
                h_dy = (metadata_layer.tileheight * tile_y_slope) / 2.0
                pygame.draw.lines(screen, color_blue, True, [
                    (mx,                          my                            - (h_avg - h_dx - h_dy)),
                    (mx + avatar_layer.tilewidth, my                            - (h_avg + h_dx - h_dy)),
                    (mx + avatar_layer.tilewidth, my + avatar_layer.tileheight  - (h_avg + h_dx + h_dy)),
                    (mx,                          my + avatar_layer.tileheight  - (h_avg - h_dx + h_dy))
                ], 2)

            px, py = self.renderer.world_to_screen(avatar_layer, avatar.rect.x, avatar.rect.y)
            pygame.draw.rect(screen, color_red, [px, py, avatar.rect.width, avatar.rect.height], 2)
