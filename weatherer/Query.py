import datetime
from collections import OrderedDict

import netCDF4
import numpy as np
from dateutil.relativedelta import relativedelta

DEFAULT_START = datetime.datetime(1979, 1, 1)
DEFAULT_END = datetime.datetime(1989, 1, 1)
DEFAULT_STEP = 'monthly'
DEFAULT_POINT = [40., -112.]
DEFAULT_BOX = [35., 45., -117., -107.]
USA_BOX = [24., 50., -133., -65.]
WA_BOX = [45., 51., -125., -116.]
DEFAULT_DATA = 'tcdc'
DEFAULT_URL = 'http://nomads.ncdc.noaa.gov/dods/NCEP_NARR_DAILY/200001/200001/' \
              'narr-a_221_200001dd_hh00_000'


def get_month_span(start, end):
    return (end.year - start.year) * 12 + (end.month - start.month)


class QueryParameters:
    """
    This class holds and generates the parameters needed to send a complete query to the
    NOMADS NCDC database, most importantly the correct time, geographic,
    and observation domains.
    """

    def __init__(self,
                 time_start=DEFAULT_START, time_end=DEFAULT_END,
                 time_resolution=DEFAULT_STEP, geo_range=WA_BOX,
                 measure=DEFAULT_DATA, state='NA'):

        self.time_start = time_start
        self.time_end = time_end
        self.time_resolution = time_resolution
        self.geo_range = geo_range
        self.state = state
        self.measure = measure

        self.months = get_month_span(self.time_start, self.time_end)
        self.master_url = 'http://nomads.ncdc.noaa.gov/dods/NCEP_NARR'

        self.domain_urls = []
        self.time_indices = []
        self.models = []
        self.lat_indices, self.lon_indices = [], []
        self.geo_range_indices = []
        self.query_name = ''
        self.queries = OrderedDict()

        self.set_master_url()
        self.set_domain_urls()
        self.set_domain_indices()
        self.get_models()
        self.get_indices()
        self.set_geo_range_indices()
        self.build_queries()
        self.set_query_name()

        del self.models

    def set_master_url(self):
        """
        Set the master URL template, which will be prepared via strftime
        """
        if self.time_resolution in ['hourly', 'daily']:
            self.master_url += '_DAILY/%Y%m/%Y%m/narr-a_221_%Y%mdd_hh00_000'
        elif self.time_resolution in ['monthly']:
            self.master_url += '_MONTHLY_AGGREGATIONS/narrmon'
            self.master_url += '-a_221'
            self.master_url += '_complete'

    def set_domain_urls(self):
        """
        Generate URLs for each time domain in the measurement period.
        """
        # Hourly increments by month
        urls = []
        if self.time_resolution in ['hourly', 'daily']:
            t = self.time_start.replace(day=1)
            urls.append(t)

            for i in xrange(0, self.months - 1):
                t = t + relativedelta(months=1)
                urls.append(t)

            if self.months > 0:
                urls.append(t + relativedelta(months=1))
        elif self.time_resolution in ['monthly']:
            urls.append(self.time_start)  # Meaningless

        self.domain_urls = [u.strftime(self.master_url) for u in urls]

    def set_domain_indices(self):
        """
        Set the time domain indices for each URL in the measurement period.
        """
        # Hourly increments by month
        if self.time_resolution in ['hourly', 'daily']:
            t = self.time_start.replace(day=1)

            if self.months == 0:
                # Then the whole range is subtended by time_start and time_end
                self.time_indices.append([(self.time_start.day - 1) * 8,
                                          (self.time_end.day - 1) * 8])
            elif self.months > 0:
                # Otherwise, the initial month has no bound on the right side
                self.time_indices.append([(self.time_start.day - 1) * 8, None])

                for i in xrange(0, self.months - 1):
                    # Non-initial, non-final months are unbounded
                    t = t + relativedelta(months=1)
                    self.time_indices.append([None, None])

                # And the final month has no bound on the left side
                self.time_indices.append([None, (self.time_start.day - 1) * 8])

            for i, td in enumerate(self.time_indices):
                if self.time_resolution in ['daily']:
                    # Should include 'aggregate' variable, but for now let 'daily' imply
                    # an aggregate of the 8 hourly periods
                    self.time_indices[i].append(None)
                else:
                    self.time_indices[i].append(None)
        # Monthly is contained in a single domain
        elif self.time_resolution in ['monthly']:
            start = get_month_span(datetime.datetime(1979, 1, 1), self.time_start)
            end = start + get_month_span(self.time_start, self.time_end)
            self.time_indices.append([start, end + 1, None])

        return

    def get_models(self):
        """
        Connect to each model in the measurement period via netCDF4.
        """
        for url_date in self.domain_urls:
            self.models.append(netCDF4.Dataset(url_date))

    def get_indices(self):
        """
        Retrieve latitude and longitude ranges for each model in the measurement period.
        """
        for m in self.models:
            self.lat_indices.append(m.variables[u'lat'][:])
            self.lon_indices.append(m.variables[u'lon'][:])

    def set_geo_range_indices(self):
        """
        Convert specified geographic range to array indices for each model.
        """
        gr = self.geo_range
        for la, lo in zip(self.lat_indices, self.lon_indices):
            indices = [np.abs(la - gr[0]).argmin() - 4,
                       np.abs(la - gr[1]).argmin() + 4,
                       np.abs(lo - gr[2]).argmin() - 4,
                       np.abs(lo - gr[3]).argmin() + 4]
            self.geo_range_indices.append(indices)

    def build_queries(self):
        """
        Assemble each query into a portable format.
        """
        for i, date in enumerate(self.domain_urls):
            self.queries[date] = {'geo_range': self.geo_range,
                                  'measurement': self.measure,
                                  'domain_url': self.domain_urls[i],
                                  'time_indices': self.time_indices[i],
                                  'time_resolution': self.time_resolution,
                                  'lat_indices': self.geo_range_indices[i][0:2],
                                  'lon_indices': self.geo_range_indices[i][2:4]
                                  }

    def set_query_name(self):
        """
        Generate the name for this entire query.
        """
        string = [self.time_start.strftime("%Y%m%d"),
                  self.time_end.strftime("%Y%m%d"),
                  self.measure,
                  self.time_resolution,
                  self.state,
                  str(int(self.geo_range[0])) + "," + str(int(self.geo_range[2])),
                  str(int(self.geo_range[1])) + "," + str(int(self.geo_range[3]))]

        self.query_name = '_'.join(string)

    @staticmethod
    def generate_query_name(d):
        """
        yyyymmdd_yyyymmdd_meas_resolution_state_rng
        :param d:
        :type d:
        :return:
        :rtype:
        """
        string = [d['time_start'].strftime("%Y%m%d"),
                  d['time_end'].strftime("%Y%m%d"),
                  d['measure'],
                  d['time_resolution'],
                  d['state'],
                  str(int(d['geo_range'][0])) + "," + str(int(d['geo_range'][2])),
                  str(int(d['geo_range'][1])) + "," + str(int(d['geo_range'][3]))]

        query_name = '_'.join(string)
        return query_name
