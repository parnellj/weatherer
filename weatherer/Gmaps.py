from __future__ import division
import pickle
import os
from datetime import datetime
import googlemaps
import numpy as np


SAVEDIR = os.path.join('.', 'outputs','gmap_queries')

with open(os.path.join('config', 'api_key.txt'), 'r') as f:
            t = []
            for line in f.readlines():
                t.append(tuple(line[:-1].split(' = ')))
            token = dict(t)

GM = googlemaps.Client(key=token['api_key'])
NOW = datetime.now()


def gm_request(gm_fun, query):
    name = gm_fun + '_'.join(query.itervalues())
    try:
        dataset = pickle.load(open(SAVEDIR + name, 'rb'))
    except IOError:
        if gm_fun == 'geocode':
            dataset = GM.geocode(address=query['address'])
        elif gm_fun == 'directions':
            dataset = GM.directions(query['start'], query['end'], mode='driving',
                                    departure_time=NOW)
        pickle.dump(dataset, open(SAVEDIR + name, 'wb'))
    return dataset


def get_bounding_box(address, pad=0):
    geocode = gm_request(gm_fun='geocode', query={'address': address})
    choices = [g[u'geometry'][u'bounds'] for g in geocode]
    bbox = [min([c[u'southwest'][u'lat'] for c in choices]) - pad,
            max([c[u'northeast'][u'lat'] for c in choices]) + pad,
            min([c[u'southwest'][u'lng'] for c in choices]) - pad,
            max([c[u'northeast'][u'lng'] for c in choices]) + pad]
    return bbox


def get_point(address):
    geocode = gm_request(gm_fun='geocode', query={'address': address})
    return geocode[0]['geometry']['location']  # ['lat', 'lng']


def get_route(start, end):
    geocode = gm_request(gm_fun='directions', query={'start': start, 'end': end})

    b = geocode[0][u'bounds']
    pad = 5

    # PRONE TO ERROR.  CHECK!
    new_bounds = np.array(
        [b[u'southwest'][u'lat'] - pad,
         b[u'northeast'][u'lat'] + pad,
         b[u'southwest'][u'lng'] - pad,
         b[u'northeast'][u'lng'] + pad])

    r = []
    dist = []
    s = u'start_location'
    e = u'end_location'

    for a in geocode[0][u'legs'][0][u'steps']:
        r.append([a[s][u'lat'], a[s][u'lng']])
        dist.append(a[u'distance'][u'value'] / 1000)

    r_fine = []
    st = 50

    for i, coord in enumerate(r[:-1]):
        s = r[i]
        e = r[i + 1]
        d = dist[i]
        ct = d / st
        # If the linspace would make <= 2 points, just return start/end
        if ct <= 2:
            r_fine.append(s)
            continue

        ct = int(np.around(ct, 0))

        spaced = zip(np.linspace(s[0], e[0], ct), np.linspace(s[1], e[1], ct))
        for p in spaced: r_fine.append(list(p))

    r_fine = np.floor(np.array(r_fine) * (16 / 3)) * (3 / 16)

    print len(r_fine)
    return r_fine, new_bounds


if __name__ == '__main__':
    usa = GM.geocode(address="United States of America")
    washington = GM.geocode(address="Washington, USA")
