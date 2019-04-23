#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import math
import argparse
import pygame
import tiledtmxloader

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def main():
    map_filename = os.path.join(THIS_DIR, 'data', 'maps', 'world.tmx')
    print("~ Map: '{}'".format(map_filename))
    map = tiledtmxloader.tmxreader.TileMapParser().parse_decode(map_filename)
    resources = tiledtmxloader.helperspygame.ResourceLoaderPygame()
    resources.load(map)
    assert map.orientation == "orthogonal"
    renderer = tiledtmxloader.helperspygame.RendererPygame()
    all_sprite_layers = []

    for idx, layer in enumerate(resources.world_map.layers):
        layer_level = int(layer.properties.get('Level', 0))
        if layer.is_object_group:
            print("Objects Layer '{}' ({}): {}".format(layer.name, 'visible' if layer.visible else 'not visible', layer.properties))
            #json.dump(layer, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
            for obj in layer.objects:
                obj_id = obj.properties.get('Id', None)
                obj_type = obj.properties.get('Type', None)
                if obj_type == 'avatar':
                    print("Avatar '{}' ('{}') at x={}, y={}".format(obj_id, obj_type, obj.x, obj.y))
                else:
                    print("Object '{}' ('{}') at x={}, y={}".format(obj_id, obj_type, obj.x, obj.y))
        else:
            print("Tiled Layer '{}' ({}): {} ({}x{})".format(layer.name, 'visible' if layer.visible else 'not visible',
                layer.properties, layer.width, layer.height))
            sprite_layer = tiledtmxloader.helperspygame.get_layer_at_index(idx, resources)
            all_sprite_layers.append(sprite_layer)

    return 0 # OK

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='World Demo')
    parser.add_argument('-v', '--verbose', action="store_true", help="verbose output" )
    args = parser.parse_args()

    if args.verbose:
        print("~ Verbose!")
    else:
        print("~ Not so verbose")

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen_width_px = 1024
    screen_height_px = 768
    screen = pygame.display.set_mode((screen_width_px, screen_height_px), pygame.DOUBLEBUF, 32)
    sys.exit(main())
