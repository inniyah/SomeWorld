#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tiledtmxloader
import sys
import os
import math
import glob
import re
import pygame

DIR_SOUTH = 1<<4
DIR_WEST  = 2<<4
DIR_NORTH = 3<<4
DIR_EAST  = 4<<4

MOVE_STAND = 0
MOVE_RLEG  = 1
MOVE_CLEG  = 2
MOVE_LLEG  = 3

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

        self.images = {}
        w = 32
        h = 48
        for dir, y in [
            (DIR_SOUTH, 0 * h),
            (DIR_WEST,  1 * h),
            (DIR_EAST,  2 * h),
            (DIR_NORTH, 3 * h),
        ]:
            for move, x in [
                (MOVE_RLEG,  0 * w),
                (MOVE_STAND, 1 * w),
                (MOVE_LLEG,  2 * w),
            ]:
                rect = pygame.Rect((x, y, w, h))
                image = pygame.Surface(rect.size, pygame.SRCALPHA, 32).convert_alpha()
                image.blit(spritesheet, (0, 0), rect)
                self.images[move | dir] = image
            self.images[MOVE_CLEG | dir] = self.images[MOVE_STAND | dir]

        try:
            self.dir = DIR_NORTH
            image = self.images[MOVE_STAND | self.dir]
            rect = image.get_rect()
            rect.midbottom = (start_pos_x, start_pos_y)
        except:
            image = None
            rect = None

        super().__init__(image, rect)

    def move(self, step_x, step_y):
        if step_x == 0 and step_y == 0:
            dir = self.dir
        elif abs(step_x) == abs(step_y):
            if step_x > 0 and (self.dir == DIR_EAST or self.dir == DIR_WEST):   dir = DIR_EAST
            elif step_x < 0 and (self.dir == DIR_EAST or self.dir == DIR_WEST): dir = DIR_WEST
            elif step_y < 0: dir = DIR_NORTH
            else: dir = DIR_SOUTH 
        elif abs(step_x) > abs(step_y):
            if step_x >= 0: dir = DIR_EAST
            else:           dir = DIR_WEST
        else:
            if step_y >= 0: dir = DIR_SOUTH
            else:           dir = DIR_NORTH

        midbottom = self.rect.midbottom
        image = self.images[MOVE_STAND | dir]
        rect = image.get_rect()
        rect.midbottom = midbottom
        self.image = image
        self.rect = rect

        self.pos_x += step_x
        self.pos_y += step_y
        self.rect.midbottom = (self.pos_x, self.pos_y)

        self.dir = dir

class Hero(Avatar):
    def __init__(self, start_pos_x, start_pos_y, path):
        super().__init__(start_pos_x, start_pos_y, path)
