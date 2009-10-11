#!/usr/bin/env python
"""A simple script that polls a data file for changes and then updates
the mayavi pipeline automatically.

This script is based heavily on the poll_file.py exampe in the mayavi distribution.


This script is to be run like so::

 $ mayavi2 -x mayaviDaemon.py ???

Or::

 $ python mayaviDaemon.py ???
 
The script currently defaults to using the example data in
examples/data/heart.vtk.  You can try editing that data file or change
this script to point to other data which you can edit.
"""

# Author: Jonathan Guyer <guyer@nist.gov>

# Based on poll_file.py
#
# Author: Prabhu Ramachandran <prabhu@aero.iitb.ac.in>
# Copyright (c) 2006-2007, Enthought Inc.
# License: BSD Style.

# Standard imports.
import os
import sys

# Enthought library imports
from enthought.mayavi.plugins.app import Mayavi
from enthought.mayavi.sources.vtk_file_reader import VTKFileReader
from enthought.pyface.timer.api import Timer

# FiPy library imports
from fipy.tools.numerix import array, concatenate, where, zeros

######################################################################
class MayaviDaemon(Mayavi):
    """Given a file name and a mayavi2 data reader object, this class
    polls the file for any changes and automatically updates the
    mayavi pipeline.
    """
    def parse_command_line(self, argv):
        """Parse command line options.

        Parameters
        ----------

        - argv : `list` of `strings`

          The list of command line arguments.
        """
        from optparse import OptionParser
        usage = "usage: %prog [options]"
        parser = OptionParser(usage)

        parser.add_option("-l", "--lock", action="store", dest="lock", type="string", default=None,
                          help="path of lock file")

        parser.add_option("-c", "--cell", action="store", dest="cell", type="string", default=None,
                          help="path of cell vtk file")

        parser.add_option("-f", "--face", action="store", dest="face", type="string", default=None,
                          help="path of face vtk file")

        parser.add_option("--xmin", action="store", dest="xmin", type="float", default=None,
                          help="minimum x value")

        parser.add_option("--xmax", action="store", dest="xmax", type="float", default=None,
                          help="maximum x value")

        parser.add_option("--ymin", action="store", dest="ymin", type="float", default=None,
                          help="minimum y value")

        parser.add_option("--ymax", action="store", dest="ymax", type="float", default=None,
                          help="maximum y value")

        parser.add_option("--zmin", action="store", dest="zmin", type="float", default=None,
                          help="minimum z value")

        parser.add_option("--zmax", action="store", dest="zmax", type="float", default=None,
                          help="maximum z value")

        parser.add_option("--datamin", action="store", dest="datamin", type="float", default=None,
                          help="minimum data value")

        parser.add_option("--datamax", action="store", dest="datamax", type="float", default=None,
                          help="maximum data value")

        (options, args) = parser.parse_args(argv)
        
        self.lockfname = options.lock
        self.cellfname = options.cell
        self.facefname = options.face
        self.extent = [options.xmin, options.xmax, 
                       options.ymin, options.ymax, 
                       options.zmin, options.zmax]
                       
        self.datamin = options.datamin
        self.datamax = options.datamax
        
    def run(self):
        # 'mayavi' is always defined on the interpreter.
        mayavi.new_scene()

        extent = zeros((0, 6))
        
        self.cellsource = self.setup_source(self.cellfname)
        if self.cellsource is not None:
            tmp = [out.cell_data.scalars for out in self.cellsource.outputs \
                   if out.cell_data.scalars is not None]
            self.has_cell_scalars = (len(tmp) > 0)
            tmp = [out.cell_data.vectors for out in self.cellsource.outputs \
                   if out.cell_data.vectors is not None]
            self.has_cell_vectors = (len(tmp) > 0)
            tmp = [out.cell_data.tensors for out in self.cellsource.outputs \
                   if out.cell_data.tensors is not None]
            self.has_cell_tensors = (len(tmp) > 0)

            extent = concatenate((extent, 
                                  [out.bounds for out in self.cellsource.outputs]),
                                 axis=0)


        self.facesource = self.setup_source(self.facefname)
        if self.facesource is not None:
            tmp = [out.point_data.scalars for out in self.facesource.outputs \
                   if out.point_data.scalars is not None]
            self.has_face_scalars = (len(tmp) > 0)
            tmp = [out.point_data.vectors for out in self.facesource.outputs \
                   if out.point_data.vectors is not None]
            self.has_face_vectors = (len(tmp) > 0)
            tmp = [out.point_data.tensors for out in self.facesource.outputs \
                   if out.point_data.tensors is not None]
            self.has_face_tensors = (len(tmp) > 0)
            
            extent = concatenate((extent, 
                                  [out.bounds for out in self.facesource.outputs]),
                                 axis=0)
                                 
        extentmin = extent.min(axis=0)
        extentmax = extent.max(axis=0)
        
        extent = (extentmin[0], extentmax[1], 
                  extentmin[2], extentmax[3], 
                  extentmin[4], extentmax[5])

        self.extent = where(self.extent == array((None,)),
                            extent, 
                            self.extent).astype(float)

        self.view_data()

        # Poll the lock file.
        self.timer = Timer(1000, self.poll_file)
    
    def poll_file(self):
        if os.path.isfile(self.lockfname):
            self.update_pipeline(self.cellsource)
            self.update_pipeline(self.facesource)
            os.unlink(self.lockfname)

    def update_pipeline(self, source):
        """Override this to do something else if needed.
        """
        if source is not None:
            # Force the reader to re-read the file.
            source.reader.modified()
            source.update()
            # Propagate the changes in the pipeline.
            source.data_changed = True
        
    def setup_source(self, fname):
        """Given a VTK file name `fname`, this creates a mayavi2 reader
        for it and adds it to the pipeline.  It returns the reader
        created.
        """
        if fname is None:
            return None
            
        source = VTKFileReader()
        source.initialize(fname)
        mayavi.add_source(source)
        
        return source

    def view_data(self):
        """Sets up the mayavi pipeline for the visualization.
        """
        from enthought.mayavi import mlab
        from enthought.tvtk.api import tvtk
            
        if self.cellsource is not None:
#             print self.cellsource.traits()
#             print self.cellsource.__class__.__dict__
            
            clip = mlab.pipeline.data_set_clipper(self.cellsource)
            clip.filter.inside_out = True
#             clip.filter.value = self.extent
#             print clip.filter.clip_function

#             clip.filter.clip_function.set_bounds(self.extent)
            clip.widget.widget_mode = 'Box'
            clip.widget.update_implicit_function()
            clip.widget.implicit_function.set_bounds(self.extent)
#             planes = tvtk.Planes()
#             clip.widget.widget.get_planes(planes)
#             planes.set_bounds(self.extent)
# # #             clip.widget.widget.trait_modified = True
#             clip.widget.trait_modified = True
#             clip.update_data()

#             clip.widget.visible = False
            # = self.extent
#             o = mlab.pipeline.outline(clip) #, extent=self.extent)
            if self.has_cell_scalars:
                s = mlab.pipeline.surface(clip, vmin=self.datamin, vmax=self.datamax) # , extent=self.extent
    #             s.module_manager.scalar_lut_manager.show_scalar_bar = True
            p = mlab.pipeline.cell_to_point_data(clip)
            if self.has_cell_tensors:
                v = mlab.pipeline.vectors(p, vmin=self.datamin, vmax=self.datamax) # , extent=self.extent

#         if self.facesource is not None:
#             if self.has_face_scalars:
#                 s = mlab.pipeline.surface(self.facesource, extent=self.extent, vmin=self.datamin, vmax=self.datamax)
#         #     s.module_manager.scalar_lut_manager.show_scalar_bar = True
#             if self.has_face_vectors:
#                 v = mlab.pipeline.vectors(self.facesource, extent=self.extent, vmin=self.datamin, vmax=self.datamax)

def main(argv=None):
    """Simple helper to start up the mayavi application.  This returns
    the running application."""
    m = MayaviDaemon()
    m.main(argv)
    return m

if __name__ == '__main__':
    main(sys.argv[1:])
