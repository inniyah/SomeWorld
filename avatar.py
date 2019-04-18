#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tiledtmxloader
import sys
import os
import math
import glob
import re
import pygame

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
        self.spritesheet = pygame.image.load(filename).convert()
        self.images = []
        for rectangle in [(0, 0, 32, 48),(33, 0, 32, 48)]:
            rect = pygame.Rect(rectangle)
            image = pygame.Surface(rect.size, pygame.SRCALPHA, 32).convert_alpha()
            image.blit(self.spritesheet, (0, 0), rect)
            self.images.append(image)

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
