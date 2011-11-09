
import math
from imagekit.lib import Image, ImageFilter, ImageChops

class _Resize(object):
    width = None
    height = None

    def __init__(self, width=None, height=None):
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height

    def process(self, img):
        raise NotImplementedError('process must be overridden by subclasses.')


class Crop(_Resize):
    """
    Resizes an image , cropping it to the specified width and height.

    """
    TOP_LEFT = 'tl'
    TOP = 't'
    TOP_RIGHT = 'tr'
    BOTTOM_LEFT = 'bl'
    BOTTOM = 'b'
    BOTTOM_RIGHT = 'br'
    CENTER = 'c'
    LEFT = 'l'
    RIGHT = 'r'

    _ANCHOR_PTS = {
        TOP_LEFT: (0, 0),
        TOP: (0.5, 0),
        TOP_RIGHT: (1, 0),
        LEFT: (0, 0.5),
        CENTER: (0.5, 0.5),
        RIGHT: (1, 0.5),
        BOTTOM_LEFT: (0, 1),
        BOTTOM: (0.5, 1),
        BOTTOM_RIGHT: (1, 1),
    }

    def __init__(self, width=None, height=None, anchor=None):
        """
        :param width: The target width, in pixels.
        :param height: The target height, in pixels.
        :param anchor: Specifies which part of the image should be retained
            when cropping. Valid values are:

            - Crop.TOP_LEFT
            - Crop.TOP
            - Crop.TOP_RIGHT
            - Crop.LEFT
            - Crop.CENTER
            - Crop.RIGHT
            - Crop.BOTTOM_LEFT
            - Crop.BOTTOM
            - Crop.BOTTOM_RIGHT

        """
        super(Crop, self).__init__(width, height)
        self.anchor = anchor

    def process(self, img):
        cur_width, cur_height = img.size
        horizontal_anchor, vertical_anchor = Crop._ANCHOR_PTS[self.anchor or \
                Crop.CENTER]
        ratio = max(float(self.width) / cur_width, float(self.height) / cur_height)
        resize_x, resize_y = ((cur_width * ratio), (cur_height * ratio))
        crop_x, crop_y = (abs(self.width - resize_x), abs(self.height - resize_y))
        x_diff, y_diff = (int(crop_x / 2), int(crop_y / 2))
        box_left, box_right = {
            0:   (0, self.width),
            0.5: (int(x_diff), int(x_diff + self.width)),
            1:   (int(crop_x), int(resize_x)),
        }[horizontal_anchor]
        box_upper, box_lower = {
            0:   (0, self.height),
            0.5: (int(y_diff), int(y_diff + self.height)),
            1:   (int(crop_y), int(resize_y)),
        }[vertical_anchor]
        box = (box_left, box_upper, box_right, box_lower)
        img = img.resize((int(resize_x), int(resize_y)), Image.ANTIALIAS).crop(box)
        return img


class Fit(_Resize):
    """
    Resizes an image to fit within the specified dimensions.

    """
    def __init__(self, width=None, height=None, upscale=None):
        """
        :param width: The maximum width of the desired image.
        :param height: The maximum height of the desired image.
        :param upscale: A boolean value specifying whether the image should
            be enlarged if its dimensions are smaller than the target
            dimensions.

        """
        super(Fit, self).__init__(width, height)
        self.upscale = upscale

    def process(self, img):
        cur_width, cur_height = img.size
        if not self.width is None and not self.height is None:
            ratio = min(float(self.width) / cur_width,
                        float(self.height) / cur_height)
        else:
            if self.width is None:
                ratio = float(self.height) / cur_height
            else:
                ratio = float(self.width) / cur_width
        new_dimensions = (int(round(cur_width * ratio)),
                          int(round(cur_height * ratio)))
        if new_dimensions[0] > cur_width or \
           new_dimensions[1] > cur_height:
            if not self.upscale:
                return img
        img = img.resize(new_dimensions, Image.ANTIALIAS)
        return img


def histogram_entropy(im):
    """
    Calculate the entropy of an images' histogram. Used for "smart cropping" in easy-thumbnails;
    see: https://raw.github.com/SmileyChris/easy-thumbnails/master/easy_thumbnails/utils.py
    
    """
    if not isinstance(im, Image.Image):
        return 0 # Fall back to a constant entropy.
    
    histogram = im.histogram()
    hist_ceil = float(sum(histogram))
    histonorm = [histocol / hist_ceil for histocol in histogram]
    
    return -sum([p * math.log(p, 2) for p in histonorm if p != 0])


class Trim(object):
    """
    Trims away the solid border color from an image. Defaults to trimming white borders.
    The Trim processor is based on the implementation of 'autocrop' from easy-thumbnails:
    
        https://github.com/SmileyChris/easy-thumbnails/blob/master/easy_thumbnails/processors.py#L76
    
    """
    def __init__(self, trim_luma=255):
        self.trim_luma = trim_luma
    
    def process(self, img):
        bw = img.convert('1')
        bw = bw.filter(ImageFilter.MedianFilter)
        
        # fill a new image with the background and subtract it.
        bg = Image.new('1', img.size, self.trim_luma)
        diff = ImageChops.difference(bw, bg)
        
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        
        return img



