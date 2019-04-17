#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse
import freetype2
import numpy
import pyglet
from pyglet import gl

THIS_DIR = os.path.dirname(os.path.realpath(__file__))

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

class TrueTypeMonoFont():
  def __init__(self, font_name, size):
    FT = freetype2.FT # easier access to constants
    self.lib = freetype2.get_default_lib()

    # Load font  and check it is monotype
    face = self.lib.find_face(font_name)
    face.set_char_size(size=size, resolution=90)
    if face.face_flags & FT.FACE_FLAG_FIXED_WIDTH  == 0:
        raise 'Font is not monotype'

    # Determine largest glyph size
    width, height, ascender, descender = 0, 0, 0, 0
    for c in range(32,128):
        face.load_char(c, FT.LOAD_RENDER | FT.LOAD_FORCE_AUTOHINT)
        bitmap    = face.glyph.bitmap
        width     = max( width, bitmap.width )
        ascender  = max( ascender, face.glyph.bitmap_top )
        descender = max( descender, bitmap.rows-face.glyph.bitmap_top )
    height = ascender+descender

    # Generate texture data
    Z = numpy.zeros((height*6, width*16), dtype=numpy.ubyte)
    for j in range(6):
        for i in range(16):
            face.load_char(32+j*16+i, FT.LOAD_RENDER | FT.LOAD_FORCE_AUTOHINT )
            bitmap = face.glyph.bitmap.copy_with_array()
            x = i*width  + face.glyph.bitmap_left
            y = j*height + ascender - face.glyph.bitmap_top
            Z[y:y+bitmap.rows,x:x+bitmap.width].flat = bitmap.buffer

    # Bound texture
    self.texture_ids = (pyglet.gl.GLuint * 1) ()
    gl.glGenTextures(1, self.texture_ids)
    self.texture_id = self.texture_ids[0]
    gl.glBindTexture( gl.GL_TEXTURE_2D, self.texture_id )
    gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR )
    gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR )
    gl.glTexImage2D( gl.GL_TEXTURE_2D, 0, gl.GL_ALPHA, Z.shape[1], Z.shape[0],
                     0, gl.GL_ALPHA, gl.GL_UNSIGNED_BYTE, Z.tostring() )

    # Generate display lists
    dx, dy = width/float(Z.shape[1]), height/float(Z.shape[0])
    self.base = gl.glGenLists(8*16)
    for i in range(8*16):
        c = chr(i)
        x = i % 16
        y = i // 16 - 2
        gl.glNewList(self.base+i, gl.GL_COMPILE)
        if (c == '\n'):
            gl.glPopMatrix( )
            gl.glTranslatef( 0, -height, 0 )
            gl.glPushMatrix( )
        elif (c == '\t'):
            gl.glTranslatef( 4*width, 0, 0 )
        elif (i >= 32):
            gl.glBegin( gl.GL_QUADS )
            gl.glTexCoord2d( (x  )*dx, (y+1)*dy ), gl.glVertex2d( 0,     -height )
            gl.glTexCoord2d( (x  )*dx, (y  )*dy ), gl.glVertex2d( 0,     0 )
            gl.glTexCoord2d( (x+1)*dx, (y  )*dy ), gl.glVertex2d( width, 0 )
            gl.glTexCoord2d( (x+1)*dx, (y+1)*dy ), gl.glVertex2d( width, -height )
            gl.glEnd( )
            gl.glTranslatef( width, 0, 0 )
        gl.glEndList( )

  def write_text(self, text):
    #gl.glTexEnvf( gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE )
    #gl.glEnable( gl.GL_DEPTH_TEST )
    gl.glEnable( gl.GL_BLEND )
    #gl.glEnable( gl.GL_COLOR_MATERIAL )
    #gl.glColorMaterial( gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE )
    gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
    gl.glEnable( gl.GL_TEXTURE_2D )

    gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
    gl.glColor4f(1, 1, 0, 1)
    gl.glPushMatrix()
    gl.glLoadIdentity( )
    gl.glScalef(0.003, 0.003, 0)
    #gl.glTranslatef(10, 100, 0)
    gl.glPushMatrix()
    gl.glListBase(self.base)
    gl.glCallLists(len(text), gl.GL_UNSIGNED_BYTE, bytes(text, 'utf-8'))
    #for c in text:
    #    gl.glCallList(self.base + 1 + ord(c))
    gl.glPopMatrix()
    gl.glPopMatrix()

    gl.glDisable( gl.GL_BLEND )
    gl.glDisable( gl.GL_TEXTURE_2D )

def demo_pyglet(file_name):
    """Demonstrates loading, rendering, and traversing a Tiled map in pyglet.

    TODO:
    Maybe use this to put topleft as origin:
        gl.glMatrixMode(GL_PROJECTION);
        gl.glLoadIdentity();
        gl.glOrtho(0.0, (double)mTarget->w, (double)mTarget->h, 0.0, -1.0, 1.0);

    """

    font = TrueTypeMonoFont("Liberation Mono", 64)

    world_map = tiledtmxloader.tmxreader.TileMapParser().parse_decode(file_name)
    #json.dump(world_map, sys.stdout, cls=JSONDebugEncoder, indent=2, sort_keys=True)

    # delta is the x/y position of the map view.
    # delta is a list so that it can be accessed from the on_draw method of
    # window and the update function. Note that the position is in integers to
    # match Pyglet Sprites. Using floating-point numbers causes graphical
    # problems. See http://groups.google.com/group/pyglet-users/browse_thread/thread/52f9ae1ef7b0c8fa?pli=1
    delta = [200, -world_map.pixel_height+150]
    frames_per_sec = 1.0 / 30.0
    window = pyglet.window.Window()

    @window.event
    def on_draw():
        window.clear()
        gl.glLoadIdentity() # Reset the "eye" back to the default location.
        gl.glTranslatef(delta[0], delta[1], 0.0) # Move the "eye" to the current location on the map.
        batch.draw()

        #font.write_text("Test")

    keys = pyglet.window.key.KeyStateHandler()
    window.push_handlers(keys)
    resources = tiledtmxloader.helperspyglet.ResourceLoaderPyglet()
    resources.load(world_map)

    def update(dt):
        speed = (3 + keys[pyglet.window.key.LSHIFT] * 6) * \
                int(dt / frames_per_sec)

        if keys[pyglet.window.key.LEFT]:
            delta[0] += speed
        if keys[pyglet.window.key.RIGHT]:
            delta[0] -= speed
        if keys[pyglet.window.key.UP]:
            delta[1] -= speed
        if keys[pyglet.window.key.DOWN]:
            delta[1] += speed

    # Generate the graphics for every visible tile.
    batch = pyglet.graphics.Batch()
    sprites = []
    for group_num, layer in enumerate(world_map.layers):
        if not layer.visible:
            continue
        if layer.is_object_group:
            # This is unimplemented in this minimal-case example code.
            # Should you as a user of tmxreader need this layer,
            # I hope to have a separate demo using objects as well.
            continue
        group = pyglet.graphics.OrderedGroup(group_num)
        for ytile in range(layer.height):
            for xtile in range(layer.width):
                image_id = layer.content2D[xtile][ytile]
                if image_id:
                    image_file = resources.indexed_tiles[image_id][2]
                    # The loader needed to load the images upside-down to match
                    # the tiles to their correct images. This reversal must be
                    # done again to render the rows in the correct order.
                    sprites.append(pyglet.sprite.Sprite(image_file,
                        world_map.tilewidth * xtile,
                        world_map.tileheight * (layer.height - ytile),
                        batch=batch, group=group))

    pyglet.clock.schedule_interval(update, frames_per_sec)
    pyglet.app.run()


#  -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='World Demo')
    parser.add_argument('-v', '--verbose', action="store_true", help="verbose output" )
    args = parser.parse_args()

    if args.verbose:
        print("~ Verbose!")
    else:
        print("~ Not so verbose")

    path_to_map = os.path.join(os.path.dirname(__file__), 'data', 'maps', 'world.tmx')
    #demo_pyglet("./tiledtmxloader/examples/001-1.tmx")
    demo_pyglet(path_to_map)

#  -----------------------------------------------------------------------------

if __name__ == '__main__':
    # import cProfile
    # cProfile.run('main()', "stats.profile")
    # import pstats
    # p = pstats.Stats("stats.profile")
    # p.strip_dirs()
    # p.sort_stats('time')
    # p.print_stats()
    main()
