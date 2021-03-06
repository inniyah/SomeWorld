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
        self.tile_x = None
        self.tile_y = None

        super().__init__(image, rect)

    def add_to_sprite_layer(self, sprite_layer):
        if sprite_layer not in self.sprite_layers:
            sprite_layer.add_sprite(self)
            print("Added avatar sprite '{}' to sprite layer '{}'".format(self.id, sprite_layer.name))
            self.sprite_layers.add(sprite_layer)

    def remove_from_sprite_layer(self, world, sprite_layer):
        if sprite_layer in self.sprite_layers:
            if sprite_layer.contains_sprite(self):
                sprite_layer.remove_sprite(self)
                print("Removed avatar sprite '{}' to sprite layer '{}'".format(self.id, sprite_layer.name))
            self.sprite_layers.discard(sprite_layer)

    def remove_from_all_sprite_layers(self):
        for sprite_layer in self.sprite_layers:
            if sprite_layer.contains_sprite(self):
                sprite_layer.remove_sprite(self)
                print("Removed avatar sprite '{}' to sprite layer '{}'".format(self.id, sprite_layer.name))
        self.sprite_layers.clear()

    def adjust_position(self, world):
        metadata_layer = world.get_metadata_layer(self.layer).sprite_layer
        pos_x, pos_y, tile_x, tile_y, tile_avg_height, tile_x_slope, tile_y_slope, sprite, tiles = self.get_map_pos_height_info(world, metadata_layer)
        if not tile_avg_height is None:
            h_avg = metadata_layer.tileheight * tile_avg_height
            h_dx = metadata_layer.tileheight * tile_x_slope
            h_dy = metadata_layer.tileheight * tile_y_slope
            rel_x = (pos_x - tile_x * metadata_layer.tilewidth) / metadata_layer.tilewidth - 0.5
            rel_y = (pos_y - tile_y * metadata_layer.tileheight) / metadata_layer.tileheight - 0.5
            self.z = h_avg + h_dx * rel_x + h_dy * rel_y;
            #print("Avatar sprite '{}'; z={} ({} + {} * {} + {} * {})".format(self.id, self.z, h_avg, h_dx, rel_x, h_dy, rel_y))
        else:
            self.z = 0

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
        self.adjust_position(world)

        if self.z >= world.VPIXELS_PER_LAYER:
            print("Avatar sprite '{}' going up (z={})".format(self.id, self.z))
            self.move_to_layer_level(world, self.layer + 1)
            self.pos_y -= world.VPIXELS_PER_LAYER
            self.adjust_position(world)
        elif self.z < 0:
            print("Avatar sprite '{}' going down (z={})".format(self.id, self.z))
            self.move_to_layer_level(world, self.layer - 1)
            self.pos_y += world.VPIXELS_PER_LAYER
            self.adjust_position(world)

        metadata_sprite_layer = world.get_metadata_layer(self.layer).sprite_layer
        self.tile_x = int((self.pos_x) // metadata_sprite_layer.tilewidth)
        self.tile_y = int((self.pos_y) // metadata_sprite_layer.tileheight)

    def move_to_layer_level(self, world, new_layer_level):
        self.remove_from_all_sprite_layers()
        self.layer = new_layer_level
        sprite_layer = world.get_avatar_layer(self.layer).sprite_layer
        self.add_to_sprite_layer(sprite_layer)

    def check_collision(self, world, hero_pos_x, hero_pos_y, step_x, step_y, metadata_sprite_layer):
        """
        Checks collision of the hero against the world. Its not the best way to
        handle collision detection but for this demo it is good enough.

        :Returns: steps to add to heros current position.
        """
        collision_width = self.rect.width
        collision_height = self.COLLISION_HEIGHT

        # create avatar rect
        hero_rect = pygame.Rect(0, 0, collision_width, collision_height)
        hero_rect.midbottom = (hero_pos_x, hero_pos_y)

        # find the tile location of the avatar
        tile_x = int((hero_pos_x) // metadata_sprite_layer.tilewidth)
        tile_y = int((hero_pos_y) // metadata_sprite_layer.tileheight)

        # find the tiles around the avatar and extract their rects for collision
        tile_rects = []

        for dirx, diry, mask in [
            (-1, -1, 1<<0|1<<2), (0, -1, 1<<0), ( 1, -1, 1<<0|1<<3),
            (-1,  0,      1<<2), (0,  0,   15), ( 1,  0,      1<<3),
            (-1,  1, 1<<1|1<<2), (0,  1, 1<<1), ( 1,  1, 1<<1|1<<3)
        ]:
            this_sprite = metadata_sprite_layer.content2D[tile_y + diry][tile_x + dirx]
            if this_sprite is not None:
                this_tiles = [world.map.tiles.get(k, None) for k in this_sprite.key if k in world.map.tiles]
                if this_tiles and (int(this_tiles[0].properties.get('BlockIn', 0)) & mask):
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

        # return the step the avatar should do
        return res_step_x, res_step_y

    def try_to_move(self, world, delta_time, step_x, step_y):
        collision_width = self.rect.width
        collision_height = self.COLLISION_HEIGHT
        new_step_x, new_step_y = self.check_collision(
            world, self.pos_x, self.pos_y, step_x, step_y, world.get_metadata_layer(self.layer).sprite_layer)
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
    avatar.add_to_sprite_layer(world.get_avatar_layer(layer_id).sprite_layer)
