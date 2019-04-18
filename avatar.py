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
    def __init__(self, start_pos_x, start_pos_y, filename):
        spritesheet = pygame.image.load(filename).convert()

        self.pos_x = start_pos_x
        self.pos_y = start_pos_y
        self.layer = 1

        self.images = {}
        w = 32
        h = 48
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

        self.dir_id = DIRID_NORTH
        self.move_id = MOVEID_STAND
        self.distance = 0
        image = self.images[self.move_id | self.dir_id]
        rect = image.get_rect()
        rect.midbottom = (start_pos_x, start_pos_y)

        super().__init__(image, rect)

    def move(self, delta_time, step_x, step_y):
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

class Hero(Avatar):
    def __init__(self, start_pos_x, start_pos_y, path):
        super().__init__(start_pos_x, start_pos_y, path)
