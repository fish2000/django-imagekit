"""
Imagekit Image Processor Implementations

An ImageProcessor subclass defines a set of class variables (optional)
and a class method named "process" which processes the supplied image
using the class properties as settings. The process method can be
overridden as well, allowing the user to define their own effects
and processes as per their whim.

ImageProcessors are designed to be chainable -- ImageSpecs specify one or
more ImageProcessors to be invoked when the spec property is populated;
when more than one ImageProcessor is used in an ImageSpec, the PIL image
object returned by the processor invocation is passed to the next, which 
likewise passes its output along, until all ImageProcessors have been run.

In addition to the PIL image object, an ImageProcessor.process() class method
must return the image output format 'fmt', as a string. Most processors pass
on the 'fmt' argument with which they were called -- ensuring that the thumbnails
of a JPEG will also be JPEGs, if possible. However, some ImageProcessors will
override 'fmt', particularly if they modify the images' mode; see the code
for the Atkinsonify processor, below, for an example.

Here's the latest list of supported PIL image modes:

    http://www.pythonware.com/library/pil/handbook/index.htm

"""
import types
from imagekit.lib import *
from imagekit.neuquant import NeuQuant
#from imagekit.stentiford import StentifordModel
from imagekit.utils import logg, entropy
from imagekit.utils.memoize import memoize

try:
    import numpy
except ImportError:
    numpy = None

class ExtInterceptor(type):
    
    do_not_intercept = (
        types.FunctionType, types.MethodType, types.UnboundMethodType, types.BufferType)
    
    def __new__(cls, name, bases, attrs):
        return super(ExtInterceptor, cls).__new__(cls, name, bases, attrs)


class ImageProcessor(object):
    """
    Base image processor class.
    
    """
    __metaclass__ = ExtInterceptor
    
    @classmethod
    def process(cls, img, fmt, obj):
        return img, fmt


class Format(ImageProcessor):
    format = 'JPEG'
    extension = 'jpg'
    
    @classmethod
    def process(cls, img, fmt, obj):
        return img, cls.format


class Adjustment(ImageProcessor):
    color = 1.0
    brightness = 1.0
    contrast = 1.0
    sharpness = 1.0
    
    @classmethod
    def process(cls, img, fmt, obj):
        img = img.convert('RGB')
        for name in ['Color', 'Brightness', 'Contrast', 'Sharpness']:
            factor = getattr(cls, name.lower())
            if factor != 1.0:
                try:
                    img = getattr(ImageEnhance, name)(img).enhance(factor)
                except ValueError:
                    pass
        return img, fmt


class ICCProofTransform(ImageProcessor):
    """
    Convert the image to a destination profile with LCMS.
    
    Source image numbers are treated as per its embedded profile by default;
    this may be (losslessly) overridden by an applied profile at conversion time.
    RGB images sans ICC data will be treated as sRGB IEC61966-2.1 by default.
    Relative colorimetric is the default intent.
    
    """
    source = None
    destination = None
    proof = None
    lastTXID = None
    
    mode = 'RGB' # for now
    intent = ImageCms.INTENT_RELATIVE_COLORIMETRIC
    proof_intent = ImageCms.INTENT_ABSOLUTE_COLORIMETRIC
    transformers = {}
    
    @classmethod
    def makeTXID(cls, srcID, destination, proof=None):
        if not proof:
            return "%s>%s" % (
                srcID,
                destination.getIDString(),
            )
            
        return "%s:%s>%s" % (
            srcID,
            proof.getIDString(),
            destination.getIDString(),
        )
    
    @classmethod
    def process(cls, img, fmt, obj, source=None, destination=None, proofing=True, TXID=None):
        if img.mode == "L":
            img = img.convert(cls.mode)
            
        source = (
            source is not None and source or \
            getattr(cls, 'source', None) or \
            getattr(obj, 'icc', None) or \
            IK_sRGB
        )
        
        if not source.getIDString():
            raise AttributeError("WTF: no source profile found (including default sRGB!)")
        
        # freak out if running w/o destination profiles
        destination = destination is not None and destination or cls.destination
        if not destination:
            raise AttributeError("WTF: destination transform ICC profile '%s' doesn't exist" % destination)
        
        if proofing and cls.proof is None:
            logg.warning("ICCProofTransform.process() was invoked explicitly but without a specified proofing profile.")
            logg.warning("ICCProofTransform.process() executing as a non-proof transformation...")
        
        if TXID is not None:
            if TXID not in cls.transformers:
                raise AttributeError("WTF: the TXID %s wasn't found in ICCProofTransform.transformers[].")
        
        else:
            TXID = cls.makeTXID(source.getIDString(), destination, cls.proof)
        
        if TXID not in cls.transformers:
            
            if cls.proof:
                cls.transformers[TXID] = ImageCms.ImageCmsTransform(
                    source.lcmsinstance,
                    destination.lcmsinstance,
                    img.mode,
                    cls.mode,
                    cls.intent,
                    proof=cls.proof.lcmsinstance,
                    proof_intent=cls.proof_intent,
                )
            
            else: # fall back to vanilla non-proof transform
                cls.transformers[TXID] = ImageCms.ImageCmsTransform(
                    source.lcmsinstance,
                    destination.lcmsinstance,
                    img.mode,
                    cls.mode,
                    cls.intent,
                )
        
        cls.lastTXID = TXID
        return cls.transformers[TXID].apply(img), img.format


class ICCTransform(ImageProcessor):
    """
    Convert the image to a destination profile with LCMS.
    
    Source image numbers are treated as per its embedded profile by default;
    this may be (losslessly) overridden by an applied profile at conversion time.
    RGB images sans ICC data will be treated as sRGB IEC61966-2.1 by default.
    Relative colorimetric is the default intent.
    
    """
    source = None
    destination = None
    
    # ICCTransform.process() hands everything off to ICCProofTransform.process();
    # all it needs to do is set the kwarg proofing=False.
    @classmethod
    def process(cls, img, fmt, obj, TXID=None):
        return ICCProofTransform.process(img, fmt, obj,
            source=cls.source, destination=cls.destination,
            proofing=False, TXID=TXID)


class HSVArray(ImageProcessor):
    """
    Convert to HSV using NumPy and return as an array.
    
    """
    format = 'array'
    
    @classmethod
    def process(cls, img, fmt, obj):
        from scikits.image import color
        
        rgb_array = numpy.array(img.getdata(), numpy.uint8).reshape(img.size[0], img.size[1], 3)
        hsv_array = color.rgb2hsv(rgb_array.astype(numpy.float32) / 255)
        return hsv_array, 


class NeuQuantize(ImageProcessor):
    """
    Extract and return a 256-color quantized LUT of the images' dominant colors.
    Return as a 16 x 16 x 3 array (or a PIL image if format is set to 'JPEG').
    
    """
    structure = 'PIL'
    quantfactor = 10
    width = 16 # for JPEG output
    height = 16 # for JPEG output
    resize_mode = Image.NEAREST # for JPEG output
    
    @classmethod
    def process(cls, img, fmt, obj):
        quant = NeuQuant(img.convert("RGBA"), cls.quantfactor)
        out = numpy.array(quant.colormap).reshape(16, 16, 4)
        if cls.structure == 'array':
            return out.T[0:3].T, cls.structure
        else:
            outimg = Image.new('RGBA', (16, 16), (0,0,0))
            outimg.putdata([tuple(t[0]) for t in out.T[0:3].T.reshape(256, 1, 3).tolist()])
            outimg.resize((cls.width, cls.height), cls.resize_mode)
            return outimg, fmt


class Atkinsonify(Format):
    format = 'PNG'                      # default; 'BMP' should also work.
    extension = format.lower()
    threshold = 128.0
    
    @classmethod
    def process(cls, img, fmt, obj):
        return Atkinsonify_YoDogg.process(img, fmt, obj)

class Atkinsonify_YoDogg(Format):
    """
    Apply the Atkinson dither/halftone algorithm to the image.
    A minimal implementation, adapted from Michael Migurski's
    minimal python script:
        
        http://mike.teczno.com/img/atkinson.py
    
    ... so designated as minimal by Mr. Migurski himself; I changed
    nothing of consequence when wiring his snippet into this class.
    
    ImageProcessor yield is a 1-bit image that will remind you of HyperCard;
    run it to see what I mean, or look here: 
        
        http://mike.teczno.com/notes/atkinson.html (Mr. Migurski's relevant post)
        http://verlagmartinkoch.at/software/dither/index.html (another example)
        http://en.wikipedia.org/wiki/Dither#cite_ref-10 (a comparative explanation)
        http://www.tinrocket.com/hyperdither-mac (an optimized nostalgic implementation)
    
    """
    format = 'PNG'                      # default; 'BMP' should also work.
    extension = format.lower()
    threshold = 128.0
    
    @classmethod
    def process(cls, img, fmt, obj):
        img = img.convert('L')
        threshold_matrix = int(cls.threshold)*[0] + int(cls.threshold)*[255]
        
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                
                old = img.getpixel((x, y))
                new = threshold_matrix[old]
                err = (old - new) >> 3 # divide by 8.
                img.putpixel((x, y), new)
                
                for nxy in [(x+1, y), (x+2, y), (x-1, y+1), (x, y+1), (x+1, y+1), (x, y+2)]:
                    try:
                        img.putpixel(nxy, img.getpixel(nxy) + err)
                    except IndexError:
                        pass # it happens, evidently.
        
        return img, cls.format


#@memoize
def get_stentiford_model(max_checks=None):
    from imagekit.stentiford import StentifordModel
    if max_checks is None:
        max_checks = Stentifordize.max_checks
    return StentifordModel(max_checks=max_checks)

def get_ext_stentiford_model(max_checks=None):
    from imagekit.ext.processors import StentifordModel
    if max_checks is None:
        max_checks = Stentifordize.max_checks
    return StentifordModel(max_checks=max_checks)

def get_stentiford_image(img):
    stenty = get_ext_stentiford_model()
    stenty.ogle(img)
    return stenty.pilimage

class Stentifordize(ImageProcessor):
    max_checks = 55
    
    @classmethod
    def process(cls, img, fmt, obj):
        return get_stentiford_image(img), fmt


class Reflection(ImageProcessor):
    background_color = '#FFFFFF'
    size = 0.0
    opacity = 0.6
    
    @classmethod
    def process(cls, img, fmt, obj):
        # convert bgcolor string to rgb value
        background_color = ImageColor.getrgb(cls.background_color)
        # handle palleted images
        img = img.convert('RGB')
        # copy orignial image and flip the orientation
        reflection = img.copy().transpose(Image.FLIP_TOP_BOTTOM)
        # create a new image filled with the bgcolor the same size
        background = Image.new("RGB", img.size, background_color)
        # calculate our alpha mask
        start = int(255 - (255 * cls.opacity)) # The start of our gradient
        steps = int(255 * cls.size) # the number of intermedite values
        increment = (255 - start) / float(steps)
        mask = Image.new('L', (1, 255))
        for y in range(255):
            if y < steps:
                val = int(y * increment + start)
            else:
                val = 255
            mask.putpixel((0, y), val)
        alpha_mask = mask.resize(img.size)
        # merge the reflection onto our background color using the alpha mask
        reflection = Image.composite(background, reflection, alpha_mask)
        # crop the reflection
        reflection_height = int(img.size[1] * cls.size)
        reflection = reflection.crop((0, 0, img.size[0], reflection_height))
        # create new image sized to hold both the original image and the reflection
        composite = Image.new("RGB", (img.size[0], img.size[1]+reflection_height), background_color)
        # paste the orignal image and the reflection into the composite image
        composite.paste(img, (0, 0))
        composite.paste(reflection, (0, img.size[1]))
        # Save the file as a JPEG
        fmt = 'JPEG'
        # return the image complete with reflection effect
        return composite, fmt


class Resize(ImageProcessor):
    width = None
    height = None
    crop = False
    upscale = False
    
    @classmethod
    def process(cls, img, fmt, obj):
        cur_width, cur_height = img.size
        if cls.crop:
            crop_horz = getattr(obj, obj._ik.crop_horz_field, 1)
            crop_vert = getattr(obj, obj._ik.crop_vert_field, 1)
            ratio = max(float(cls.width)/cur_width, float(cls.height)/cur_height)
            resize_x, resize_y = ((cur_width * ratio), (cur_height * ratio))
            crop_x, crop_y = (abs(cls.width - resize_x), abs(cls.height - resize_y))
            x_diff, y_diff = (int(crop_x / 2), int(crop_y / 2))
            box_left, box_right = {
                0: (0, cls.width),
                1: (int(x_diff), int(x_diff + cls.width)),
                2: (int(crop_x), int(resize_x)),
            }[crop_horz]
            box_upper, box_lower = {
                0: (0, cls.height),
                1: (int(y_diff), int(y_diff + cls.height)),
                2: (int(crop_y), int(resize_y)),
            }[crop_vert]
            box = (box_left, box_upper, box_right, box_lower)
            img = img.resize((int(resize_x), int(resize_y)), Image.ANTIALIAS).crop(box)
        else:
            if not cls.width is None and not cls.height is None:
                ratio = min(float(cls.width)/cur_width,
                            float(cls.height)/cur_height)
            else:
                if cls.width is None:
                    ratio = float(cls.height)/cur_height
                else:
                    ratio = float(cls.width)/cur_width
            new_dimensions = (int(round(cur_width*ratio)),
                              int(round(cur_height*ratio)))
            if new_dimensions[0] > cur_width or \
               new_dimensions[1] > cur_height:
                if not cls.upscale:
                    return img, fmt
            img = img.resize(new_dimensions, Image.ANTIALIAS)
        return img, fmt


class SmartCrop(ImageProcessor):
    """
    Crop an image 'smartly' -- based on smart crop implementation from easy-thumbnails:
    
        https://github.com/SmileyChris/easy-thumbnails/blob/master/easy_thumbnails/processors.py#L193
    
    Smart cropping whittles away the parts of the image with the least entropy.
    
    """
    width = None
    height = None
    
    @classmethod
    def compare_entropy(cls, start_slice, end_slice, slice, difference):
        """
        Calculate the entropy of two slices (from the start and end of an axis),
        returning a tuple containing the amount that should be added to the start
        and removed from the end of the axis.
        
        see: https://raw.github.com/SmileyChris/easy-thumbnails/master/easy_thumbnails/processors.py
        """
        start_entropy = entropy(start_slice)
        end_entropy = entropy(end_slice)
        if end_entropy and abs(start_entropy / end_entropy - 1) < 0.01:
            # Less than 1% difference, remove from both sides.
            if difference >= slice * 2:
                return slice, slice
            half_slice = slice // 2
            return half_slice, slice - half_slice
        if start_entropy > end_entropy:
            return 0, slice
        else:
            return slice, 0
    
    @classmethod
    def process(cls, img, fmt, obj):
        source_x, source_y = img.size
        diff_x = int(source_x - min(source_x, cls.width))
        diff_y = int(source_y - min(source_y, cls.height))
        left = top = 0
        right, bottom = source_x, source_y
        
        while diff_x:
            slice = min(diff_x, max(diff_x // 5, 10))
            start = img.crop((left, 0, left + slice, source_y))
            end = img.crop((right - slice, 0, right, source_y))
            add, remove = cls.compare_entropy(start, end, slice, diff_x)
            left += add
            right -= remove
            diff_x = diff_x - add - remove
        
        while diff_y:
            slice = min(diff_y, max(diff_y // 5, 10))
            start = img.crop((0, top, source_x, top + slice))
            end = img.crop((0, bottom - slice, source_x, bottom))
            add, remove = cls.compare_entropy(start, end, slice, diff_y)
            top += add
            bottom -= remove
            diff_y = diff_y - add - remove
        
        box = (left, top, right, bottom)
        img = img.crop(box)
        
        return img, fmt


class Trim(ImageProcessor):
    """
    Trims the solid border color from an image. Defaults to trimming white borders.
    The Trim processor is based on the implementation of 'autocrop' from easy-thumbnails:
    
        https://github.com/SmileyChris/easy-thumbnails/blob/master/easy_thumbnails/processors.py#L76
    
    """
    trim_luma = 255 # remove white borders
    
    @classmethod
    def process(cls, img, fmt, obj):
        bw = img.convert('1')
        bw = bw.filter(ImageFilter.MedianFilter)
        # White background.
        bg = Image.new('1', img.size, cls.trim_luma)
        diff = ImageChops.difference(bw, bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        return img, fmt


class Transpose(ImageProcessor):
    """
    Rotates or flips the image.
    
    Method should be one of the following strings:
        - FLIP_LEFT RIGHT
        - FLIP_TOP_BOTTOM
        - ROTATE_90
        - ROTATE_270
        - ROTATE_180
        - auto
    
    If method is set to 'auto', the processor will attempt to rotate the image
    according to any EXIF Orientation data it can find.
    
    """
    EXIF_ORIENTATION_STEPS = {
        1: [],
        2: ['FLIP_LEFT_RIGHT'],
        3: ['ROTATE_180'],
        4: ['FLIP_TOP_BOTTOM'],
        5: ['ROTATE_270', 'FLIP_LEFT_RIGHT'],
        6: ['ROTATE_270'],
        7: ['ROTATE_90', 'FLIP_LEFT_RIGHT'],
        8: ['ROTATE_90'],
    }
    
    method = 'auto'
    
    @classmethod
    def process(cls, img, fmt, obj):
        if cls.method == 'auto':
            try:
                orientation = Image.open(obj._imgfield.file)._getexif()[0x0112]
                ops = cls.EXIF_ORIENTATION_STEPS[orientation]
            except:
                ops = []
        else:
            ops = [cls.method]
        for method in ops:
            img = img.transpose(getattr(Image, method))
        return img, fmt
