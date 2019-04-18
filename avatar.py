#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tiledtmxloader
import sys
import os
import math
import glob
import re
import pygame

# See: https://www.pygame.org/wiki/Spritesheet
class SpriteSheet(object):
    def __init__(self, filename):
        try:
            self.sheet = pygame.image.load(filename).convert()
        except pygame.error as message:
            print('Unable to load spritesheet image:', filename)
            raise SystemExit(message)
    # Load a specific image from a specific rectangle
    def image_at(self, rectangle, colorkey = None):
        "Loads image from x,y,x+offset,y+offset"
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size).convert()
        image.blit(self.sheet, (0, 0), rect)
        if colorkey is not None:
            if colorkey is -1:
                colorkey = image.get_at((0,0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image
    # Load a whole bunch of images and return them as a list
    def images_at(self, rects, colorkey = None):
        "Loads multiple images, supply a list of coordinates" 
        return [self.image_at(rect, colorkey) for rect in rects]
    # Load a whole strip of images
    def load_strip(self, rect, image_count, colorkey = None):
        "Loads a strip of images and returns them as a list"
        tups = [(rect[0]+rect[2]*x, rect[1], rect[2], rect[3])
                for x in range(image_count)]
        return self.images_at(tups, colorkey)

class Avatar(tiledtmxloader.helperspygame.SpriteLayer.Sprite):
    def __init__(self, start_pos_x, start_pos_y, path):
        self.spritesheet = SpriteSheet(path)
        self.images = self.spritesheet.images_at([(0, 0, 32, 48),(33, 0, 32, 48)], colorkey=-1)

        try:
            image = self.images[0]
            rect = image.get_rect()
            rect.midbottom = (start_pos_x, start_pos_y)
        except:
            image = None
            rect = None
        super().__init__(image, rect)

class Hero(Avatar):
    def __init__(self, start_pos_x, start_pos_y, path):
        super().__init__(start_pos_x, start_pos_y, path)
