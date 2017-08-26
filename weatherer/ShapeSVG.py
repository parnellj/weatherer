from __future__ import division

import os

import numpy as np
import wand.color
import wand.display
import wand.image

dest = os.path.join('.', 'outputs', 'visualizations')
sample_file = "_tcdc_Greys_4xzoom_0.25px_150dpi_0.25in_bleed_1.0in_border_outline.png"


def make_mask(mask_dir, mask_file):
    """
    Sets the blue of target mask_file to transparent, and saves as 'mask.png'
    :param mask_dir:
    :type mask_dir:
    :param mask_file:
    :type mask_file:
    :return:
    :rtype:
    """
    with wand.image.Image(filename=mask_dir + '/' + mask_file) as img:
        with wand.color.Color('#0000FF') as blue:
            img.transparent_color(blue, alpha=0.0, fuzz=120)
        img.save(filename=mask_dir + '/' + 'mask.png')


def make_masks(mask_dir):
    for sub_dir in os.walk(mask_dir, topdown=False):
        if 'mask.png' in sub_dir[2]:
            print 'already created mask, continuing...'
            continue
        if len(sub_dir[2]) == 0:
            print 'no files in sub_dir, please generate at least one for masking'
            continue

        print sub_dir
        with wand.image.Image(filename=sub_dir[0] + '/' + sub_dir[2][0]) as img:
            with wand.color.Color('#0000FF') as white:
                img.transparent_color(white, alpha=0.0, fuzz=120)
            img.save(filename=sub_dir[0] + '/' + 'mask.png')
            # with wand.image.Image(filename=dir + '/' + file) as img:
            #     with wand.color.Color('#0000FF') as blue:
            #         # This fuzz value (120) minimizes the appearance of blue without clipping the
            #         # outside portion of the border.  Determined empirically.
            #         img.transparent_color(blue, alpha=0.0, fuzz=120)
            #     img.save(filename=dir + '/' + 'test_mask_' + str(120) + '.png')


def build_canvas(width, height, dpi, mask_file, source_file, file_dir, out_file,
                 bleed=0.25, mat_width=1.0, pad_width=0.25, colorspace='cmyk',
                 mat_color='#ffffff', pad_color='#ffffff',
                 detail_px=800, save_intermediate=False,
                 display_each=False, final_size=1000, watermark=False):
    # Bleed, mat, and pad are passed in inches, so convert to pixels
    bleed_px = int(dpi * bleed)
    mat_px = int(dpi * mat_width)
    pad_px = int(dpi * pad_width)

    # Mat and pad are included in the passed width.  Bleed is in addition.
    canvas_w_px = (width * dpi) + bleed_px
    canvas_h_px = (height * dpi) + bleed_px

    canvas_bg_color = wand.color.Color(string=mat_color)
    with wand.image.Image(width=canvas_w_px,
                          height=canvas_h_px, background=canvas_bg_color) as canvas:
        source = wand.image.Image(filename=file_dir + source_file)

        # Create a zoomed detail, if specified
        if detail_px is not None:
            mid_w, mid_h = (np.array(source.size) / 2).astype(int)
            zoom_span = int(detail_px / 2)
            # try:
            with wand.image.Image(source) as detail:
                detail.crop()
                print 'left: ' + str(mid_w - zoom_span)
                print 'top: ' + str(mid_h - zoom_span)
                print 'right: ' + str(mid_w + zoom_span)
                print 'bottom: ' + str(mid_h + zoom_span)
                detail.crop(mid_w - zoom_span, mid_h - zoom_span,
                            mid_w + zoom_span, mid_h + zoom_span)
                detail.save(filename=file_dir + '4_detail_' + out_file + '.png')
            # except ValueError:
            #     print 'ValueError: no detail made for ' + out_file
            #     print 'mid_h: ' + str(mid_h) + 'mid_w: ' + str(mid_w)
            #     print 'zoom_span: ' + str(zoom_span)

        # Load the mask.
        # Resize it to the dimensions of the source image.
        # Composite the mask on top of the source image (cookie cutter).
        # Watermark the new source image.
        with wand.image.Image(filename=file_dir + mask_file) as mask:
            mask.resize(*np.array(source.size))
            source.composite(image=mask, left=0, top=0)
            print str(mask.size)
            print str(source.size)
            if watermark:
                with wand.image.Image(filename="../resources/watermarks/wm.png") as wm:
                    wm.crop(left=0, top=0, width=source.width, height=source.height)
                    source.watermark(image=wm, transparency=0.95)
            with wand.image.Image(image=source) as m:
                resize_factor = final_size / max(m.size)
                m.resize(width=int(m.width * resize_factor),
                         height=int(m.height * resize_factor))
                m.save(filename=file_dir + '3_nomat_' + out_file + '.png')

        if save_intermediate:
            source.save(filename=file_dir + '_mask' + out_file + '.png')
        if display_each:
            raw_input('showing masked, enter when done')
            wand.display.display(source)

        # Create a new pad canvas on which to put the image so far.  Size matches the
        # source image plus the required padding.
        # Composite the source image, centered, on top of the pad.
        # Resize the newly-composited pad image to fit the final canvas dimensions.
        pad_bg_color = wand.color.Color(string=pad_color)
        pad_w, pad_h = np.array(source.size) + pad_px * 2
        with wand.image.Image(width=pad_w, height=pad_h, background=pad_bg_color) as pad:
            print 'pad size: ' + str(pad.size)
            print 'src size: ' + str(source.size)
            print 'pad_px: ' + str(pad_px)
            pad.composite(image=source, left=pad_px, top=pad_px)
            if save_intermediate:
                pad.save(filename=file_dir + '_pad' + out_file + '.png')
            if display_each:
                wand.display.display(pad)
                raw_input('showing padded, enter when done')

            pad_w, pad_h = pad.size
            target_w, target_h = np.array(canvas.size) - mat_px * 2 - bleed_px * 2
            if (pad_w / pad_h) > (target_w / target_h):
                scale_factor = target_w / pad_w
            else:
                scale_factor = target_h / pad_h

            new_w, new_h = (np.array(pad.size) * scale_factor).astype(int)
            pad.resize(width=new_w, height=new_h)
            x_off, y_off = ((np.array(canvas.size) - np.array(pad.size)) / 2).astype(int)
            canvas.composite(image=pad, left=x_off, top=y_off)
            canvas.transform_colorspace(colorspace_type=colorspace)
            if final_size is not None:
                resize_factor = final_size / max(canvas.size)
                canvas.resize(width=int(canvas.width * resize_factor),
                              height=int(canvas.height * resize_factor))
            canvas.save(filename=file_dir + '2_mat_' + out_file + '.png')
            if display_each:
                wand.display.display(canvas)
                raw_input('showing matted, enter when done')

            if width > height:
                mockup = "../resources/mockup_frames/landscape_alt.png"
                mock_off_x, mock_off_y = (147, 222)
                img_size_x, img_size_y = (716, 512)
                mock_x, mock_y = (1000 - 218, 1761 - 535)
            else:
                mockup = "../resources/mockup_frames/portrait_alt.png"
                mock_off_x, mock_off_y = (222, 137)
                img_size_x, img_size_y = (512, 716)
                mock_x, mock_y = (1761 - 535, 2046 - 329)

            img_ratio = img_size_x / img_size_y

        # Load the appropriate mockup as a new wand Image.
        #

        with wand.image.Image(filename=mockup) as mock:
            new_canvas = wand.image.Image(width=mock.width, height=mock.height,
                                          background=canvas_bg_color)
            print 'mockup size: ' + str(mock.size)
            with wand.image.Image(filename=file_dir + '2_mat_' + out_file + '.png') as c:
                c_w, c_h = c.size
                if (c_w / c_h) > (img_size_x / img_size_y):
                    scale_factor = img_size_x / c_w
                else:
                    scale_factor = img_size_y / c_h
                new_w, new_h = (np.array(c.size) * scale_factor).astype(int)
                c.resize(width=new_w, height=new_h)
                print 'loaded canvas size: ' + str(c.size)
                x_off = int((img_size_x - c.width) / 2)
                y_off = int((img_size_y - c.height) / 2)
                mock.composite(image=c, left=mock_off_x + x_off,
                               top=mock_off_y + y_off)
                if final_size is not None:
                    resize_factor = final_size / max(mock.size)
                    mock.resize(width=int(mock.width * resize_factor),
                                height=int(mock.height * resize_factor))
                new_canvas.composite(image=mock, left=0, top=0)
                new_canvas.save(filename=file_dir + '1_mockup_' + out_file + '.png')
        source.close()


def crop(directory):
    for fname in os.listdir(directory):
        new_name = fname[11:fname.find("_4x")] + '_swatch.png'
        with wand.image.Image(filename=dest + '/' + fname) as img:
            img.crop(left=787, top=509, width=465, height=464)
            with wand.image.Image(filename=directory + '\\' +
                    'circle_mask_no_aa.png') as mask:
                img.composite(mask, top=0, left=0)
            with wand.color.Color('#000000') as black:
                img.transparent_color(black, alpha=0.0, fuzz=0)
            img.save(filename=dest + '/' + new_name)


if __name__ == '__main__':
    pass
