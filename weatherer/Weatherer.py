import csv
import os
import pickle
from datetime import datetime
from shutil import copyfile

import numpy as np
from pydap.client import open_url

import Gmaps
import ShapeSVG
from Datasets import Dataset, Result
from Draw import Animator
from Query import QueryParameters

SAVEDIR = os.path.join('outputs', '_orders')
VIZ_SUBDIR = 'visualizations'


def load_requests(csv_file):
    with open(csv_file) as f:
        entries = [{k: v for k, v in row.items()}
                   for row in csv.DictReader(f, skipinitialspace=True)]
    viz_params, queries = [], []

    for e in entries:
        viz_params.append(
            dict(address=e['address'], state=e['state'], measure=e['measure'],
                 cmap=e['cmap'], zoom=int(e['zoom']), interpolate=int(e['interpolate']),
                 prefix=e['prefix'], cmap_name=e['cmap_name'],
                 stroke_width=e['stroke_width'], width=int(e['width']),
                 bleed=float(e['bleed']), mat_width=float(e['mat_width']),
                 pad_width=float(e['pad_width']), colorspace=e['colorspace'],
                 height=int(e['height']), dpi=int(e['dpi']), flag=e['flag'],
                 mat_color=e['mat_color'], pad_color=e['pad_color']))

        queries.append(dict(time_start=datetime.strptime(e['time_start'], "%Y%m%d"),
                            time_end=datetime.strptime(e['time_end'], "%Y%m%d"),
                            measure=e['measure'], time_resolution=e['time_resolution'],
                            geo_range=e['geo_range'], state=e['state']))

    return zip(viz_params, queries)


def load_ds(query_params):
    if query_params.query_name in os.listdir('../outputs/pickles/'):
        print 'loading saved ds'
        data = pickle.load(open('../outputs/pickles/' + query_params.query_name, 'rb'))
    else:
        print 'generating new ds'
        data = Dataset(execute_query(query_params.queries))
        pickle.dump(data, open('../outputs/pickles/' + query_params.query_name, 'wb'))
    return data


def load_query(query_params):
    query_name = QueryParameters.generate_query_name(query_params)
    if query_name in os.listdir('../outputs/ds_queries/'):
        qp = pickle.load(open('../outputs/ds_queries/' + query_name, 'rb'))
    else:
        print 'generating new query'
        qp = QueryParameters(**query_params)
        pickle.dump(qp, open('../outputs/ds_queries/' + query_name, 'wb'))
    return qp


def execute_query(queries):
    results = []
    for k, q in queries.iteritems():
        ti = q['time_indices']
        la = q['lat_indices']
        lo = q['lon_indices']
        model = open_url(q['domain_url'])
        d = model[q['measurement']][ti[0]:ti[1]:ti[2], la[0]:la[1], lo[0]:lo[1]]

        for i, t in enumerate(d.time):
            try:
                unit = d.attributes['units']
            except KeyError:
                unit = 'NA'
            r = Result(q['geo_range'], q['measurement'], t, q['time_resolution'], unit,
                       d.attributes['long_name'], d.attributes['missing_value'],
                       np.array(d[q['measurement']][i]), np.array(d['lat'][:]),
                       np.array(d['lon'][:]))
            results.append(r)
    return results


def visualize(p, query, prefix=''):
    """
    Generate and save visualizations based on the passed parameters.

    1. Get the appropriate geographic bounding box coordinates from Google Maps
    2. Generate a query based on these coordinates and the passed measurement
    3. Download (or unpickle) the appropriate dataset
        3a. Perform operations on the dataset
    4. Generate the outline image
        4a. Save as a 1200 DPI SVG
        4b. Edit the SVG to appropriate stroke thickness
        4c. Save new SVG
        4d. Convert the new SVG to a PNG named "mask.png" if this does not already exist
    5. Generate the data image
        5a, 5b, 5c. Same as above
        5d. Convert the new SVG to a PNG.
    6. Delete extraneous SVG files
    7. Request that the user construct the mask manually
    8. Composite the mask and the data image

    Final Outputs:

        1. High-res (~8k) PNG
        2. Low-res (~720p) PNG
        2. Unmasked Data SVG
    """
    if p['flag'] == 'skip':
        return

    output_path = os.path.join(SAVEDIR, VIZ_SUBDIR, p['address'])
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    output_filename = '_'.join([p['state'], p['prefix'], p['measure'], p['cmap_name'],
                                str(p['zoom']) + 'xzoom', str(p['interpolate']) + 'intrp',
                                p['stroke_width'] + 'px', str(p['dpi']) + 'dpi',
                                str(p['bleed']) + 'in_bleed',
                                str(p['mat_width']) + 'in_mat'])

    if (output_filename + '.png') in os.listdir(output_path):
        print 'file ' + output_filename + '  exists, returning...'
        return

    dataset = load_ds(query)
    dataset.fix_nans()
    dataset.zoom(p['zoom'])
    dataset.interpolate(p['interpolate'])

    a = Animator(dataset, clear_frames=False, repeat=False,
                 contour_levels=20, cmap=p['cmap'])
    a.draw_region(stroke_width=p['stroke_width'], state=p['state'])

    if 'mask.png' not in os.listdir(output_path):
        a.save_plt(output_path + output_filename + '_outline.png', width=p['width'],
                   height=p['height'], dpi=600)

    if p['flag'] != 'outline_only':
        a.stack('contour', stroke_width=p['stroke_width'])
        dims = a.save_plt(output_path + output_filename + '.png', width=p['width'],
                          height=p['height'], dpi=p['dpi'])

        if dims == 'landscape' and p['width'] < p['height']:
            new_w = p['height']
            p['height'] = p['width']
            p['width'] = new_w
        elif dims == 'portrait' and p['height'] < p['width']:
            new_h = p['width']
            p['width'] = p['height']
            p['height'] = new_h

        if p['flag'] == 'order':
            final_size = max(p['width'] * p['dpi'], p['height'] * p['dpi'])
        else:
            final_size = 1000

        ShapeSVG.build_canvas(width=p['width'], height=p['height'],
                              dpi=p['dpi'], mask_file='mask.png',
                              source_file=output_filename + '.png', file_dir=output_path,
                              out_file=output_filename + '_final.png',
                              mat_width=p['mat_width'],
                              pad_width=p['pad_width'], bleed=p['bleed'],
                              colorspace=p['colorspace'],
                              mat_color=p['mat_color'], pad_color=p['pad_color'],
                              final_size=final_size)

    copyfile('D:\Dropbox\Etsy\swatches\swatch_menu_r2.png',
             output_path + '5_palette_menu.png')

    a.close()
    del a


if __name__ == '__main__':
    requests = load_requests('../inputs/20170131_order.csv')

    for viz_params, query_params in requests:
        if query_params['geo_range'] == '':
            geo_box = Gmaps.get_bounding_box(address=viz_params['address'], pad=0.25)
        else:
            geo_box = [float(bound) for bound in query_params['geo_range'].split(',')]

        query_params['geo_range'] = geo_box
        qp = load_query(query_params)
        visualize(p=viz_params, query=qp)
