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

DIRID_SOUTH = 1<<4
DIRID_WEST  = 2<<4
DIRID_NORTH = 3<<4
DIRID_EAST  = 4<<4

MOVEID_STAND = 0
MOVEID_RLEG  = 1
MOVEID_CLEG  = 2
MOVEID_LLEG  = 3

NUM_MOVES = 4

# See: https://nerdparadise.com/programming/pygameblitopacity
def blit_alpha(target, source, location, opacity):
    x = location[0]
    y = location[1]
    temp = pygame.Surface((source.get_width(), source.get_height())).convert()
    temp.blit(target, (-x, -y))
    temp.blit(source, (0, 0))
    temp.set_alpha(opacity)        
    target.blit(temp, location)

# See: https://www.pygame.org/wiki/Spritesheet
class Avatar(tiledtmxloader.helperspygame.SpriteLayer.Sprite):
    COLLISION_HEIGHT = 5.0

    def __init__(self, start_pos_x, start_pos_y, spritesheet_filename, id=None):
        spritesheet = pygame.image.load(spritesheet_filename).convert()

        self.pos_x = start_pos_x
        self.pos_y = start_pos_y
        self.layer = 1
        self.id = id

        self.images = {}
        w = spritesheet.get_width() / 3
        h = spritesheet.get_height() / 4
        for dir_id, y in [
            (DIRID_SOUTH, 0 * h),
            (DIRID_WEST,  1 * h),
            (DIRID_EAST,  2 * h),
            (DIRID_NORTH, 3 * h),
        ]:
            for move, x in [
                (MOVEID_RLEG,  0 * w),
                (MOVEID_STAND, 1 * w),
                (MOVEID_LLEG,  2 * w),
            ]:
                rect = pygame.Rect((x, y, w, h))
                image = pygame.Surface(rect.size, pygame.SRCALPHA, 32).convert_alpha()
                image.blit(spritesheet, (0, 0), rect)
                self.images[move | dir_id] = image
            self.images[MOVEID_CLEG | dir_id] = self.images[MOVEID_STAND | dir_id]

        self.dir_id = DIRID_SOUTH
        self.move_id = MOVEID_STAND
        self.distance = 0
        image = self.images[self.move_id | self.dir_id]
        rect = image.get_rect()
        rect.midbottom = (start_pos_x, start_pos_y)

        self.sprite_layers = set()

        super().__init__(image, rect)

    def execute_move(self, world, delta_time, step_x, step_y):
        self.distance += math.sqrt(step_x**2 + step_y**2)
        self.move_id = int(self.distance / 10.) % NUM_MOVES
        if step_x == 0 and step_y == 0:
            dir_id = self.dir_id
            self.move_id = MOVEID_STAND
        elif abs(step_x) == abs(step_y):
            if step_x > 0 and (self.dir_id == DIRID_EAST or self.dir_id == DIRID_WEST):   dir_id = DIRID_EAST
            elif step_x < 0 and (self.dir_id == DIRID_EAST or self.dir_id == DIRID_WEST): dir_id = DIRID_WEST
            elif step_y < 0: dir_id = DIRID_NORTH
            else: dir_id = DIRID_SOUTH 
        elif abs(step_x) > abs(step_y):
            if step_x >= 0: dir_id = DIRID_EAST
            else:           dir_id = DIRID_WEST
        else:
            if step_y >= 0: dir_id = DIRID_SOUTH
            else:           dir_id = DIRID_NORTH

        midbottom = self.rect.midbottom
        image = self.images[self.move_id | dir_id]
        rect = image.get_rect()
        rect.midbottom = midbottom
        self.image = image
        self.rect = rect

        self.pos_x += step_x
        self.pos_y += step_y
        self.rect.midbottom = (self.pos_x, self.pos_y)

        self.dir_id = dir_id

        metadata_layer = world.metadata_layers[self.layer][1]
        pos_x, pos_y, tile_x, tile_y, tile_avg_height, tile_x_slope, tile_y_slope, sprite, tiles = self.get_map_pos_height_info(world, metadata_layer)
        if not tile_avg_height is None:
            h_avg = metadata_layer.tileheight * tile_avg_height
            h_dx = metadata_layer.tileheight * tile_x_slope
            h_dy = metadata_layer.tileheight * tile_y_slope
            self.z = h_avg + \
                h_dx * (pos_x - tile_x * metadata_layer.tilewidth) / metadata_layer.tilewidth + \
                h_dy * (pos_y - tile_y * metadata_layer.tileheight) / metadata_layer.tileheight;
        else:
            self.z = 0

    def try_to_move(self, world, delta_time, step_x, step_y):
        collision_width = self.rect.width
        collision_height = self.COLLISION_HEIGHT
        new_step_x, new_step_y = world.check_collision(self.pos_x, self.pos_y, step_x, step_y, collision_width, collision_height, world.metadata_layers[self.layer][1])
        self.execute_move(world, delta_time, new_step_x, new_step_y)

    def get_map_pos(self):
        return (self.pos_x, self.pos_y - self.COLLISION_HEIGHT/2.0)

    def get_map_pos_info(self, world, metadata_layer):
        pos_x, pos_y = self.get_map_pos()
        tile_x, tile_y, sprite, tiles = world.get_pos_info(pos_x, pos_y, metadata_layer)
        return pos_x, pos_y, tile_x, tile_y, sprite, tiles

    def get_map_pos_height_info(self, world, metadata_layer):
        pos_x, pos_y, tile_x, tile_y, sprite, tiles = self.get_map_pos_info(world, metadata_layer)
        if tiles and tiles[0]:
            tile_avg_height = tiles[0].properties.get('Height', None)
            tile_x_slope = float(tiles[0].properties.get('XSlope', 0.0))
            tile_y_slope = float(tiles[0].properties.get('YSlope', 0.0))
            if not tile_avg_height is None:
                #print("Tile: x={}, y={}, h={}, dx={}, dy={}".format(tile_x, tile_y, tile_avg_height, tile_x_slope, tile_y_slope))
                tile_avg_height = float(tile_avg_height)
        else:
            tile_avg_height = None
            tile_x_slope = 0.0
            tile_y_slope = 0.0
        return pos_x, pos_y, tile_x, tile_y, tile_avg_height, tile_x_slope, tile_y_slope, sprite, tiles

    def add_to_sprite_layer(self, sprite_layer):
       if sprite_layer not in self.sprite_layers:
            sprite_layer.add_sprite(self)
            #print("added avatar sprite to sprite layer", sprite_layer)
            self.sprite_layers.add(sprite_layer)

    def remove_from_sprite_layer(self, world, sprite_layer):
       if sprite_layer in self.sprite_layers:
            if sprite_layer.contains_sprite(self):
                sprite_layer.remove_sprite(hero)
                #print("removed avatar sprite from sprite layer", sprite_layer)
            self.sprite_layers.pop(sprite_layer, None)

    def remove_from_all_sprite_layers(self):
       for sprite_layer in sprite_layer:
            if sprite_layer.contains_sprite(self):
                sprite_layer.remove_sprite(hero)
                #print("removed avatar sprite from sprite layer", sprite_layer)
            self.sprite_layers.pop(sprite_layer, None)

class Hero(Avatar):
    def __init__(self, start_pos_x, start_pos_y, spritesheet_png):
        super().__init__(start_pos_x, start_pos_y, spritesheet_png)

def create_hero_avatar(start_pos_x, start_pos_y, spritesheet_png):
    full_spritesheet_path = os.path.join(os.path.dirname(__file__), 'data', 'avatars', spritesheet_png)
    avatar = Hero(start_pos_x, start_pos_y, full_spritesheet_path)
    return avatar

def create_avatar(world, layer_id, start_pos_x, start_pos_y, obj_id, obj_props):
    json_filename = os.path.join(os.path.dirname(__file__), 'data', 'characters', '{}.json'.format(obj_id))
    with open(json_filename) as json_file:
        json_data = json.load(json_file)
        json.dump(json_data, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
    spritesheet_png = json_data['SpriteSheet']
    full_spritesheet_path = os.path.join(os.path.dirname(__file__), 'data', 'avatars', spritesheet_png)
    avatar = Avatar(start_pos_x, start_pos_y, full_spritesheet_path, obj_id)
    world.add_avatar(avatar)
    avatar.add_to_sprite_layer(world.avatar_layers[layer_id][1])
