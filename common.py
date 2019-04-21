#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import math
import tiledtmxloader

# This class escapes a string, by replacing control characters by their hexadecimal equivalents
class escape(str): # pylint: disable=invalid-name
    def __repr__(self):
        return ''.join('\\x{:02x}'.format(ord(ch)) if ord(ch) < 32 else ch for ch in self)
    __str__ = __repr__

class JSONDebugEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        if isinstance(obj, bytes):
            return escape(obj.decode('utf-8'))
        if isinstance(obj, tiledtmxloader.tmxreader.Tile):
            return 'Tile: id={} gid={} images={} properties={}'.format(obj.id, obj.gid, obj.images, obj.properties)
        if isinstance(obj, object):
            try:
                return [
                    ['%s' % (c,) for c in type.mro(type(obj))],
                    obj.__dict__,
                ]
            except AttributeError:
                return ['%s' % (c,) for c in type.mro(type(obj))]
        try:
            ret = json.JSONEncoder.default(self, obj)
        except:
            ret = ('%s' % (obj,))
        return ret

def special_round(value):
    """
    For negative numbers it returns the value floored,
    for positive numbers it returns the value ceiled.
    """
    if value < 0:
        return math.floor(value)
    return math.ceil(value)
