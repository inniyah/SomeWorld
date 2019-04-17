# -*- coding: utf-8 -*-
#
# New BSD license
#
# Copyright (c) DR0ID
# This file is part of trunk
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL DR0ID BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
TODO: module description


Versioning scheme based on: http://en.wikipedia.org/wiki/Versioning#Designating_development_stage

::

      +-- api change, probably incompatible with older versions
      |     +-- enhancements but no api change
      |     |
    major.minor[.build[.revision]]
                   |        |
                   |        +-|* x for x bugfixes
                   |
                   +-|* 0 for alpha (status)
                     |* 1 for beta (status)
                     |* 2 for release candidate
                     |* 3 for (public) release

.. versionchanged:: 0.0.0.0
    initial version

"""
from __future__ import print_function


__version__ = '1.0.0.0'

# for easy comparison as in sys.version_info but digits only
__version_info__ = tuple([int(d) for d in __version__.split('.')])

__author__ = "DR0ID"
__email__ = "dr0iddr0id {at} gmail [dot] com"
__copyright__ = "DR0ID @ 2014"
__credits__ = ["DR0ID"]  # list of contributors
__maintainer__ = "DR0ID"
__license__ = "New BSD license"


import sys
import os

import pyglet

try:
    import _path
except:
    pass

import tiledtmxloader


def demo_pyglet(file_name):
    """Demonstrates loading, rendering, and traversing a Tiled map in pyglet.

    TODO:
    Maybe use this to put topleft as origin:
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(0.0, (double)mTarget->w, (double)mTarget->h, 0.0, -1.0, 1.0);

    """

    import pyglet
    from pyglet.gl import glTranslatef, glLoadIdentity

    world_map = tiledtmxloader.tmxreader.TileMapParser().parse_decode(file_name)
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
        # Reset the "eye" back to the default location.
        glLoadIdentity()
        # Move the "eye" to the current location on the map.
        glTranslatef(delta[0], delta[1], 0.0)
        # TODO: [21:03]	thorbjorn: DR0ID_: You can generally determine the range of tiles that are visible before your drawing loop, which is much faster than looping over all tiles and checking whether it is visible for each of them.
        # [21:06]	DR0ID_: probably would have to rewrite the pyglet demo to use a similar render loop as you mentioned
        # [21:06]	thorbjorn: Yeah.
        # [21:06]	DR0ID_: I'll keep your suggestion in mind, thanks
        # [21:06]	thorbjorn: I haven't written a specific OpenGL renderer yet, so not sure what's the best approach for a tile map.
        # [21:07]	thorbjorn: Best to create a single texture with all your tiles, bind it, set up your vertex arrays and fill it with the coordinates of the tiles currently on the screen, and then let OpenGL draw the bunch.
        # [21:08]	DR0ID_: for each layer?
        # [21:08]	DR0ID_: yeah, probably a good approach
        # [21:09]	thorbjorn: Ideally for all layers at the same time, if you don't have to draw anything in between.
        # [21:09]	DR0ID_: well, the NPC and other dynamic things need to be drawn in between, right?
        # [21:09]	thorbjorn: Right, so maybe once for the bottom layers, then your complicated stuff, and then another time for the layers on top.

        batch.draw()

    keys = pyglet.window.key.KeyStateHandler()
    window.push_handlers(keys)
    resources = tiledtmxloader.helperspyglet.ResourceLoaderPyglet()
    resources.load(world_map)

    def update(dt):
        # The speed is 3 by default.
        # When left Shift is held, the speed increases.
        # The speed interpolates based on time passed, so the demo navigates
        # at a reasonable pace even on huge maps.
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
    """
    Main method.
    """
    args = sys.argv[1:]
    if len(args) < 1:
        path_to_map = os.path.join(os.pardir, "001-1.tmx")
        print(("usage: python %s your_map.tmx\n\nUsing default map '%s'\n" % \
            (os.path.basename(__file__), path_to_map)))
    else:
        path_to_map = args[0]

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

