from __future__ import division

import os
import numpy as np
from matplotlib import pyplot as plt, animation
from matplotlib.patches import Polygon
from mpl_toolkits.basemap import Basemap

OUTPUT_REL = os.path.join('.', 'outputs', 'visualizations')


class Animator:
    """
    This class is a container for several types of animation functions, (hopefully)
    providing a cleaner and more self-contained interface than ad hoc functions.
    """

    def __init__(self, dataset, cmap="Greys", contour_levels=10, clear_frames=False,
                 repeat=True):
        """
        Does a few things:
            -> Assigns a local copy of the dataset and various switches
            -> Clears the current axis of plt
            -> Creates a new Basemap instance
            -> Sets coordinate matrices, value maxima, and the colormap
        """
        self.dataset = dataset
        self.clear_frames = clear_frames
        self.repeat = repeat
        self.init_frame = False

        # Construction of mpl table components
        plt.cla()
        self.figure = plt.figure()
        self.axis = plt.Axes(self.figure, [0., 0., 1., 1.])
        self.axis.set_axis_off()
        self.figure.add_axes(self.axis)

        middle_lat = self.dataset.globals['lat_min'] + self.dataset.globals['lat_max']
        middle_lat /= 2
        self.bmap = Basemap(projection='merc', resolution='c', ax=self.axis,
                            lat_ts=middle_lat,
                            llcrnrlat=self.dataset.globals['lat_min'],
                            urcrnrlat=self.dataset.globals['lat_max'],
                            llcrnrlon=self.dataset.globals['lon_min'],
                            urcrnrlon=self.dataset.globals['lon_max'])

        self.lon, self.lat = np.meshgrid(self.dataset.lon_array, self.dataset.lat_array)
        self.x, self.y = self.bmap(self.lon, self.lat)
        self.x = np.array(self.x)
        self.y = np.array(self.y)
        self.val_min = self.dataset.globals['val_min']
        self.val_max = self.dataset.globals['val_max']

        self.levels = np.linspace(self.val_min, self.val_max, contour_levels)
        self.cmap = plt.get_cmap(cmap)

    def adjust_dimensions(self, goal_w=36, goal_h=24):
        '''
        Preserves resolution in case of mismatch between region and paper aspect ratios.

        E.g., a very narrow map going onto a more square paper size would normally have
        its height shrunk significantly to fit; in this case, therefore, the height of
        the generated image should be increased to preserve fidelity preemptively.

        :param goal_w: the width of the target medium
        :type goal_w: int
        :param goal_h: the height of the target medium
        :type goal_h: int
        '''
        map_w = self.bmap.xmax
        map_h = self.bmap.ymax
        new_w, new_h = 0, 0

        if map_w > map_h:
            new_w = max(goal_w, goal_h)
            new_h = min(goal_w, goal_h)
            orientation = 'landscape'
        elif map_w < map_h:
            new_w = min(goal_w, goal_h)
            new_h = max(goal_w, goal_h)
            orientation = 'portrait'
        goal_w = new_w
        goal_h = new_h

        if goal_w > goal_h:
            new_dims = np.array([goal_w, goal_w * map_h / map_w])
        else:
            new_dims = np.array([goal_h * map_w / map_h, goal_h])

        if new_dims[0] < goal_w:
            new_dims = (new_dims * (goal_w / new_dims[0]))
        elif new_dims[1] < goal_h:
            new_dims = (new_dims * (goal_h / new_dims[1]))
        new_dims.astype(int)

        return {'w': new_dims[0], 'h': new_dims[1], 'orientation': orientation}

    def clear_whitespace(self):
        """
        Clears extraneous whitespace around the plot axis and figure.

        This is apparently a known "tricky thing."  This "solution" appears to
        work.  Credit to: http://stackoverflow.com/a/27227718/4272935
        """
        plt.gca().set_axis_off()
        plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
        plt.margins(0, 0)
        plt.gca().xaxis.set_major_locator(plt.NullLocator())
        plt.gca().yaxis.set_major_locator(plt.NullLocator())

    def save_plt(self, filename='', width=6, height=4, dpi=100):
        """
        Saves the plot with the specified dimensions.  At high DPIs the DPI must be
        adjusted as MPL has a hardcoded limit of <= 32768 for any image dimension.
        """
        scale = self.adjust_dimensions(goal_w=width, goal_h=height)
        self.figure.set_size_inches(w=scale['w'], h=scale['h'])

        if scale['h'] * dpi > 32768:
            dpi = int(32768 / scale['h'])
            print 'to ' + str(dpi)
        if scale['w'] * dpi > 32768:
            dpi = int(32768 / scale['w'])
            print 'to ' + str(dpi)
        self.clear_whitespace()
        self.figure.savefig(filename, dpi=dpi, bbox_inches='tight', pad_inches=0)

        return scale['orientation']

    def draw_region(self, stroke_width=1.0, state='NA'):
        """
        Draws the specified region (states for now, later, provinces or smaller countries)
        """
        if state != 'NA':
            sh = os.path.join('.', 'resources', 'sa_adm1')
            shp_info = self.bmap.readshapefile(shapefile=sh, name='states',
                                               drawbounds=False)
            for seg_num, seg in enumerate(self.bmap.states):
                if self.bmap.states_info[seg_num]['NAME_1'] in [state]:
                    p = Polygon(seg, facecolor=None, edgecolor='#000000',
                                alpha=1, zorder=1, linewidth=stroke_width,
                                antialiased=None)
                    self.axis.add_patch(p)
            self.bmap.plot(0, 0, alpha=0.0)
        for c in self.axis.collections:
            c.set_linewidth(stroke_width)

    def stack(self, plot_type, stroke_width=1.0):
        """
        Stacks a series of plots of type plot_type, via successive draw calls.
        """
        self.axis.patches = []
        plt.ion()
        # This erases the underlying outline
        for c in self.axis.collections:
            c.set_color((0., 0., 0., 0.))
        for i in range(0, self.dataset.length):
            view = self.anim_type(plot_type, self.dataset.results[i].val)
            # This allows us to change the linewidth post-hoc
            for c in view.collections:
                c.set_linewidth(stroke_width)
        plt.ioff()

    def anim(self, plot_type):
        """
        Creates and displays an animated chart of the specified type.
        """
        def anim_data():
            """
            Generator function that yields successive frames (data snapshots).
            """
            for i in range(0, self.dataset.length):
                yield self.dataset.results[i].val

        def animate(d):
            """
            Drawer function called for each frame of the animation. As with other
            plotting functions here, actual plots are drawn by anim_type()
            """
            if self.clear_frames:
                plt.cla()
                self.draw_region()

            view = self.anim_type(plot_type, d)
            if self.init_frame:
                plt.colorbar()
                self.init_frame = False
            return view

        a = animation.FuncAnimation(self.figure, animate, anim_data, repeat=self.repeat)
        plt.show()

    def anim_wind(self):
        prune = (slice(None, None, 5), slice(None, None, 5))

        def animate(i):
            plt.cla()
            view = plt.quiver(self.x[prune], self.y[prune],
                              self.dataset.results[i].val[prune],
                              self.dataset_2.results[i].val[prune], alpha=0.5)
            self.bmap.drawstates()
            self.bmap.drawmapboundary()
            self.bmap.drawcountries()
            self.bmap.drawcoastlines()
            return view

        a = animation.FuncAnimation(self.figure, animate, repeat=self.repeat)
        plt.show()

    def anim_type(self, plot_type, d):
        """
        Calls plot functions with arguments declared in the Animator constructor.
        """
        if plot_type == 'contour':
            return self.axis.contour(self.x, self.y, d,
                                     alpha=0.5, vmin=self.val_min, vmax=self.val_max,
                                     cmap=self.cmap, levels=self.levels)

        elif plot_type == 'contourf':
            return self.axis.contourf(self.x, self.y, d,
                                      alpha=0.5, vmin=self.val_min, vmax=self.val_max,
                                      cmap=self.cmap, levels=self.levels)

        elif plot_type == 'pcolormesh':
            return self.axis.pcolormesh(self.x, self.y, d,
                                        alpha=0.5, vmin=self.val_min, vmax=self.val_max,
                                        cmap=self.cmap)

        elif plot_type == 'imshow':
            return self.axis.imshow(d, alpha=0.5, cmap=self.cmap,
                                    extent=[self.x.min(), self.x.max(), self.y.min(),
                                            self.y.max()])

    def close(self):
        """
        Closes all figures, axes, and PLT instances.  Appears to serve its function of
        clearing memory.
        """
        self.figure.clf()
        plt.close()
        del self.dataset
        del self.bmap
