#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tiledtmxloader
import sys
import os
import math
import array
import glob
import re
import pygame
import vectors
from common import *
from avatar import create_avatar

class WorldLayerInfo():
    def __init__(self, idx, layer, sprite_layer):
        self.idx = idx
        self.layer = layer
        self.sprite_layer = sprite_layer

class WorldLevel():
    def __init__(self, level, tiles):
        self.level = level
        self.tiles = tiles
        self.all_layers_info = []
        self.avatar_layer = None
        self.metadata_layer = None
        self.obstacles = None

    # Type code  C Type          Python Type        Minimum size in bytes
    # 'c'        char            character          1
    # 'b'        signed char     int                1
    # 'B'        unsigned char   int                1
    # 'u'        Py_UNICODE      Unicode character  2 on narrow unicode builds, 4 on wide builds
    # 'h'        signed short    int                2
    # 'H'        unsigned short  int                2
    # 'i'        signed int      int                2
    # 'I'        unsigned int    long               2
    # 'l'        signed long     int                4
    # 'L'        unsigned long   long               4
    # 'f'        float           float              4
    # 'd'        double          float              8

    CELL_BLOCK_NW = 1<<0
    CELL_BLOCK_N  = 1<<1
    CELL_BLOCK_NE = 1<<2
    CELL_BLOCK_W  = 1<<3
    CELL_BLOCK    = 1<<4
    CELL_BLOCK_E  = 1<<5
    CELL_BLOCK_SW = 1<<6
    CELL_BLOCK_S  = 1<<7
    CELL_BLOCK_SE = 1<<8

    def fill_obstacles(self):
        print("fill_obstacles: start")
        self.obstacles = array.array('H', [0]) * (self.metadata_layer.layer.width * self.metadata_layer.layer.height)

        for tile_y in range(0, self.metadata_layer.layer.height):
            for tile_x in range(0, self.metadata_layer.layer.width):
                tile_mask = 0
                for dirx, diry, dirmask in [
                    (-1, -1, 1<<0),
                    ( 0, -1, 1<<1),
                    ( 1, -1, 1<<2),
                    (-1,  0, 1<<3),
                    ( 0,  0, 1<<4),
                    ( 1,  0, 1<<5),
                    (-1,  1, 1<<6),
                    ( 0,  1, 1<<7),
                    ( 1,  1, 1<<8),
                ]:
                    if tile_y + diry >= 0 and tile_x + dirx >= 0 and \
                        tile_y + diry < self.metadata_layer.layer.height and \
                        tile_x + dirx < self.metadata_layer.layer.width:
                            this_sprite = self.metadata_layer.sprite_layer.content2D[tile_y + diry][tile_x + dirx]
                    else:
                            this_sprite = None

                    if this_sprite is not None:
                        this_tiles = [self.tiles.get(k, None) for k in this_sprite.key if k in self.tiles]
                        if this_tiles and this_tiles[0].properties.get('Block', None) in ['true']:
                            tile_mask |= dirmask
        print("fill_obstacles: end")

    def add_layer(self, idx, layer, sprite_layer):
        if int(layer.properties.get('Level', 0)) != self.level:
            return
        layer_info = WorldLayerInfo(idx, layer, sprite_layer)
        self.all_layers_info.append(layer_info)
        if layer.properties.get('Metadata', None):
            self.metadata_layer = layer_info
            self.fill_obstacles()
        if layer.properties.get('Avatar', None):
            self.avatar_layer = layer_info

class World():
    HPIXELS_PER_METER = 32.0
    VPIXELS_PER_METER = 23.0 # 45 degrees, so 32 * sqrt(2) / 2
    METERS_PER_LAYER = 2.0
    VPIXELS_PER_LAYER = 46.0 # METERS_PER_LAYER * VPIXELS_PER_METER

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

        self.world_layers = {}
        self.all_sprite_layers = []

        for idx, layer in enumerate(self.resources.world_map.layers):
            layer_level = int(layer.properties.get('Level', 0))
            if layer.is_object_group:
                print("Objects Layer '{}' ({}): {}".format(layer.name, 'visible' if layer.visible else 'not visible', layer.properties))
                #json.dump(layer, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
                for obj in layer.objects:
                    obj_id = obj.properties.get('Id', None)
                    obj_type = obj.properties.get('Type', None)
                    if obj_type == 'avatar':
                        print("Avatar '{}' ('{}') at x={}, y={}".format(obj_id, obj_type, obj.x, obj.y))
                        create_avatar(self, layer_level, obj.x, obj.y, obj_id, obj.properties)
                    else:
                        print("Object '{}' ('{}') at x={}, y={}".format(obj_id, obj_type, obj.x, obj.y))
            else:
                print("Tiled Layer '{}' ({}): {} ({}x{})".format(layer.name, 'visible' if layer.visible else 'not visible',
                    layer.properties, layer.width, layer.height))
                if layer_level not in self.world_layers:
                    self.world_layers[layer_level] = WorldLevel(layer_level, self.map.tiles)
                sprite_layer = tiledtmxloader.helperspygame.get_layer_at_index(idx, self.resources)
                self.world_layers[layer_level].add_layer(idx, layer, sprite_layer)
                self.all_sprite_layers.append(sprite_layer)

    def get_avatar_layer(self, layer_level):
        return self.world_layers[layer_level].avatar_layer

    def get_metadata_layer(self, layer_level):
        return self.world_layers[layer_level].metadata_layer

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
        if not self.show_layer_level_up and pos_z >= 1.5 * self.VPIXELS_PER_METER:
            self.show_layer_level_up = True
            self.adjust_layer_level_visibility()
        elif self.show_layer_level_up and pos_z < 1.0 * self.VPIXELS_PER_METER:
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
            avatar_sprite_layer = self.get_avatar_layer(avatar.layer).sprite_layer
            metadata_sprite_layer = self.get_metadata_layer(avatar.layer).sprite_layer

            #pos_x, pos_y = avatar.get_map_pos()
            #pos_x, pos_y, tile_x, tile_y, sprite, tiles = avatar.get_map_pos_info(self, metadata_sprite_layer)
            pos_x, pos_y, tile_x, tile_y, tile_avg_height, tile_x_slope, tile_y_slope, sprite, tiles = avatar.get_map_pos_height_info(self, metadata_sprite_layer)

            mx = (pos_x // metadata_sprite_layer.tilewidth) * metadata_sprite_layer.tilewidth
            my = (pos_y // metadata_sprite_layer.tileheight) * metadata_sprite_layer.tileheight
            mx, my = self.renderer.world_to_screen(avatar_sprite_layer, mx, my)
            pygame.draw.rect(screen, color_blue, [mx, my,  metadata_sprite_layer.tilewidth, metadata_sprite_layer.tileheight], 2)

            if not tile_avg_height is None:
                h_avg = metadata_sprite_layer.tileheight * tile_avg_height
                h_dx = (metadata_sprite_layer.tileheight * tile_x_slope) / 2.0
                h_dy = (metadata_sprite_layer.tileheight * tile_y_slope) / 2.0
                pygame.draw.lines(screen, color_blue, True, [
                    (mx,                                   my                                     - (h_avg - h_dx - h_dy)),
                    (mx + metadata_sprite_layer.tilewidth, my                                     - (h_avg + h_dx - h_dy)),
                    (mx + metadata_sprite_layer.tilewidth, my + metadata_sprite_layer.tileheight  - (h_avg + h_dx + h_dy)),
                    (mx,                                   my + metadata_sprite_layer.tileheight  - (h_avg - h_dx + h_dy))
                ], 2)

            px, py = self.renderer.world_to_screen(avatar_sprite_layer, avatar.rect.x, avatar.rect.y)
            pygame.draw.rect(screen, color_red, [px, py, avatar.rect.width, avatar.rect.height], 2)
