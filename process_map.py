#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import io
import json
import math
import argparse
import hashlib
import tiledtmxloader
from PIL import Image

from common import *

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

def get_file_sha1sum(file_descriptor, blocksize=2**20):
    sha1sum = hashlib.sha1()
    while True:
        fbuf = file_descriptor.read(blocksize)
        if not fbuf:
            break
        sha1sum.update(fbuf)
    return sha1sum.hexdigest()

class MapResourceLoader(tiledtmxloader.tmxreader.AbstractResourceLoader):
    def load(self, tile_map):
        tiledtmxloader.tmxreader.AbstractResourceLoader.load(self, tile_map)

        for layer in self.world_map.layers:
            if layer.is_object_group:
                continue

            for gid in layer.decoded_content:
                if gid not in self.indexed_tiles:
                    if gid & self.FLIP_X or gid & self.FLIP_Y or gid & self.FLIP_DIAGONAL:
                        image_gid = gid & ~(self.FLIP_X | self.FLIP_Y | self.FLIP_DIAGONAL)
                        offset_x, offset_y, img = self.indexed_tiles[image_gid]
                        tex = img.get_texture()
                        orig_anchor_x = tex.anchor_x
                        orig_anchor_y = tex.anchor_y
                        tex.anchor_x = tex.width / 2
                        tex.anchor_y = tex.height / 2
                        if gid & self.FLIP_DIAGONAL:
                            if gid & self.FLIP_X:
                                tex2 = tex.get_transform(rotate=90)
                            elif gid & self.FLIP_Y:
                                tex2 = tex.get_transform(rotate=270)
                        else:
                            tex2 = tex.get_transform(flip_x=bool(gid & self.FLIP_X), flip_y=bool(gid & self.FLIP_Y))
                        tex2.anchor_x = tex.anchor_x = orig_anchor_x
                        tex2.anchor_y = tex.anchor_y = orig_anchor_y
                        self.indexed_tiles[gid] = (offset_x, offset_y, tex2)

        #json.dump(self.indexed_tiles, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)
        for id, (offsetx, neg_offsety, img) in self.indexed_tiles.items():
            print("~ Tile '{}' ({}, {}): {}".format(id, offsetx, neg_offsety, img))
            sha1sum = hashlib.sha1()
            output = io.BytesIO()
            img.save(output, format='PNG')
            sha1sum.update(output.getvalue())
            print("~ SHA1: {}".format(sha1sum.hexdigest()))

    def _load_image(self, filename, colorkey=None):
        img = self._img_cache.get(filename, None)
        if img is None:
            print("~ Image: '{}'".format(filename))
            img = Image.open(filename)
            self._img_cache[filename] = img
        return img

    def _load_image_file_like(self, file_like_obj, colorkey=None):
        return self._load_image(file_like_obj)

    def _load_image_part(self, filename, xpos, ypos, width, height, colorkey=None):
        #print("~ Image Part: '{}' ({}, {}, {}, {}, {})".format(filename, xpos, ypos, width, height, colorkey))
        source_img = self._load_image(filename, colorkey)
        crop_rectangle = (xpos, ypos, xpos + width, ypos + height)
        return self._load_image(filename).crop(crop_rectangle)

    def _load_image_parts(self, filename, margin, spacing, tile_width, tile_height, colorkey=None):
        source_img = self._load_image(filename, colorkey)
        width, height = source_img.size
        tile_width_spacing = tile_width + spacing
        width = (width // tile_width_spacing) * tile_width_spacing
        tile_height_spacing = tile_height + spacing
        height = (height // tile_height_spacing) * tile_height_spacing
        images = []
        for y_pos in range(margin, height, tile_height_spacing):
            for x_pos in range(margin, width, tile_width_spacing):
                img_part = self._load_image_part(filename, x_pos, y_pos, tile_width, tile_height, colorkey)
                images.append(img_part)
        return images


def main():
    map_filename = os.path.join(THIS_DIR, 'data', 'maps', 'world.tmx')
    print("~ Map: '{}'".format(map_filename))
    map = tiledtmxloader.tmxreader.TileMapParser().parse_decode(map_filename)
    resources = MapResourceLoader()
    resources.load(map)
    assert map.orientation == "orthogonal"
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
            #sprite_layer = tiledtmxloader.helperspygame.get_layer_at_index(idx, resources)
            #all_sprite_layers.append(sprite_layer)

    return 0 # OK

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='World Demo')
    parser.add_argument('-v', '--verbose', action="store_true", help="verbose output" )
    args = parser.parse_args()

    if args.verbose:
        print("~ Verbose!")
    else:
        print("~ Not so verbose")

    sys.exit(main())
