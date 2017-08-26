import copy
import datetime

import numpy as np
import scipy.ndimage


class Result:
    """
    This class stores a single result, i.e., matrices of value, latitude, and longitude
    for a given observation point.  Functions to manipulate these values and arrays
    are also provided.
    """

    def __init__(self, geo_range, measurement, time, time_resolution,
                 unit, long_name, missing_value,
                 val, lat, lon, keep_nan=False):
        self.geo_range = geo_range
        self.measurement = measurement
        self.time = time
        self.time_resolution = time_resolution
        self.unit = unit
        self.long_name = long_name

        self.missing_value = missing_value

        self.val = val
        self.lat = lat
        self.lon = lon

        self.obs_date = datetime.datetime.fromordinal(int(self.time) - 1)
        self.obs_date = self.obs_date + datetime.timedelta(hours=(self.time % 1) * 24)
        self.dt_string = ''
        self.display_title = ''
        self.update_labels()

    def convert_units(self):
        if self.unit == "K":
            self.val = ((self.val - 273.15) * 1.8) + 32
            self.unit = "F"

    def update_labels(self):
        self.dt_string = self.obs_date.strftime("%Y-%m-%d %I:%M %p")
        self.display_title = self.long_name + " " + self.dt_string + \
                             " (" + self.unit + ")"

    def zoom(self, multiplier):
        self.val = scipy.ndimage.zoom(self.val, multiplier)
        self.lat = scipy.ndimage.zoom(self.lat, multiplier)
        self.lon = scipy.ndimage.zoom(self.lon, multiplier)

    def fix_nans(self):
        self.val[self.val >= self.missing_value] = np.nan
        self.val[self.val == np.nan] = np.nanmean(self.val)


class Dataset:
    """
    This class provides a container for the list of results, as well as some global
    statistics and values for use in plotting and animating.
    """

    def __init__(self, results, agg=None):
        self.results = results
        if agg is not None:
            self.aggregate(agg)

        self.length = len(self.results)
        self.globals = {'val_min': np.inf,
                        'val_max': -np.inf,
                        'lat_min': self.results[0].geo_range[0],
                        'lat_max': self.results[0].geo_range[1],
                        'lon_min': self.results[0].geo_range[2],
                        'lon_max': self.results[0].geo_range[3]}
        print 'from results init: '
        print self.globals

        self.lon_array, self.lat_array = self.results[0].lon, self.results[0].lat
        self.set_extrema()
        return

    def set_extrema(self):
        for v in self.results:
            # self.globals['lat_min'] = min(self.globals['lat_min'], np.min(v.lat))
            # self.globals['lat_max'] = max(self.globals['lat_max'], np.max(v.lat))
            # self.globals['lon_min'] = min(self.globals['lon_min'], np.min(v.lon))
            # self.globals['lon_max'] = max(self.globals['lon_max'], np.max(v.lon))
            self.globals['val_min'] = min(self.globals['val_min'], np.min(v.val))
            self.globals['val_max'] = max(self.globals['val_max'], np.max(v.val))
        return

    def aggregate(self, results, step):
        results_agg = []
        for i in np.arange(0, len(results), step):
            results_key = results[i]
            results_key.val = np.array([r.val for r in results[i:i + step]]).mean(axis=0)
            results_agg.append(results_key)
        self.results = results.agg

    # Really more of a blur
    def interpolate(self, multiplier):
        if multiplier == 1:
            return
        results_interp = []
        keys = np.arange(0, len(self.results) - 1)
        for i in keys:
            vd = (self.results[i + 1].val - self.results[i].val) / multiplier
            td = (self.results[i + 1].obs_date - self.results[i].obs_date) / multiplier
            for j in range(0, multiplier):
                result_i = copy.deepcopy(self.results[i])
                result_i.val += (vd * (j + 1))
                result_i.obs_date += (td * (j + 1))
                result_i.update_labels()
                results_interp.append(result_i)
        results_interp.append(self.results[-1])
        self.results = results_interp
        self.length = len(results_interp)

    def zoom(self, multiplier):
        for r in self.results:
            r.zoom(multiplier)
        self.lon_array, self.lat_array = self.results[0].lon, self.results[0].lat

    def fix_nans(self):
        for r in self.results:
            r.fix_nans()

    def concat_results(self, trim=10):
        self.results = self.results[:trim]
        self.length = trim
