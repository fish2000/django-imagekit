#!/usr/bin/env python
# encoding: utf-8
"""
__init__.py

ImageKit utility functions.

Created by FI$H 2000 on 2011-09-01.
Copyright (c) 2011 Objects In Space And Time, LLC. All rights reserved.

"""
import tempfile, os, hashlib, math
from django.conf import settings
from imagekit.utils.ordereddict import OrderedDict
from imagekit.utils.json import json

class FakeLogger(object):
    """
    Completely unacceptable fake-logger class, just in case.
    """
    def log(self, level, msg):
        print msg
    
    def logg(self, msg):
        self.log(0, msg)
    
    def __init__(self, *args, **kwargs):
        super(FakeLogger, self).__init__(*args, **kwargs)
        for fname in ('critical', 'debug', 'error', 'exception', 'info', 'warning'):
            setattr(self, fname, self.logg)

# Try to use the jogging app, falling back to the python standard logging module.
# With Django 1.3, you should eschew jogging in favor of the standard, as Django 1.3
# goes out of its way to make the standard module do what jogging does and moreso.
# in any case, imagekit internals should import the 'logg' object from django.utils.
try:
    from jogging import logging as logg
except ImportError:
    try:
        import logging
        logg = logging.getLogger("imagekit")
    except ImportError:
        print "SRSLY: You have no logging facilities available whatsoever, so we're using a fake logger class. Love, Django ImageKit."
        # set up fake logger
        logg = FakeLogger()

def img_to_fobj(img, format, **kwargs):
    """
    Given a PIL instance and an output format type,
    return a temporary disk filehandle for use in spec accessor(s).
    Integrates Photoshop CMYK fix from https://github.com/jdriscoll/django-imagekit/commit/25f628de9311a66780961e74fa03e1696ee3bf79
    
    """
    tmp = tempfile.TemporaryFile()
    
    # preserve transparency if the image is in Pallette (P) mode
    # from https://github.com/ryanbagwell/django-imagekit/blob/db95e63a632bc0bd62f1842bda8ef30e0e6df6ff/imagekit/utils.py
    if img.mode == 'P':
        kwargs['transparency'] = 255
    else:
        img.convert('RGB')
    
    img.save(tmp, format, **kwargs)
    tmp.seek(0)
    return tmp

def entropy(im):
    """
    Calculate the entropy of an images' histogram. Used for "smart cropping" in easy-thumbnails;
    see: https://raw.github.com/SmileyChris/easy-thumbnails/master/easy_thumbnails/utils.py
    
    """
    from PIL import Image
    
    if not isinstance(im, Image.Image):
        # Can only deal with PIL images. Fall back to a constant entropy.
        return 0
    
    hist = im.histogram()
    hist_size = float(sum(hist))
    hist = [h / hist_size for h in hist]
    
    return -sum([p * math.log(p, 2) for p in hist if p != 0])

class ADict(dict):
    """
    ADict -- Convenience class for dictionary key access via attributes.
    
    The 'A' in 'ADict' is for 'Access' -- you can also use adict.key as well as adict[key]
    to access hash values.
    
    """
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
    
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(name)
    
    def __setattr__(self, name, value):
        self[name] = value


class AODict(ADict, OrderedDict):
    """
    AODict -- an OrderedDict subclass that works like ADict.
    
    The 'O' in 'AODict' is for 'Ordered' -- see the stdlib OrderedDict for deets, or refer to
    the reimplementation in ordereddict.py, if your python install is lacking.
    
    """
    def __init__(self, *args, **kwargs):
        OrderedDict.__init__(self, *args, **kwargs)
    
    def __setattr__(self, name, value):
        if name == "_keys":
            object.__setattr__(self, name, value)
        else:
            self[name] = value


# Get the xy coordinate tuple from the Yxy representation of an XYZ value.
xy = lambda n: (n.X / (n.X + n.Y + n.Z), n.Y / (n.X + n.Y + n.Z))

# get the URL for a static asset (e.g. ImageKit's css/js/etc)
static = lambda pth: os.path.join(settings.STATIC_URL, 'imagekit', pth)

# convert a triple of 8-bit values (like what you get out of PIL) to #000000 format.
hexstr = lambda triple: "#%02X%02X%02X" % tuple(triple)

# hash an ICC profile object
icchash = lambda icc: hashlib.sha1(icc.data).hexdigest()


# color dicts for admin and templates.
class SeriesColors(ADict):
    def __init__(self):
        self.R = "#FF1919"
        self.G = "#19FA19"
        self.B = "#1991FF"
        self.L = "#CCCCCC"

class SeriesColorsAlpha(ADict):
    def __init__(self):
        self.R = "rgba(165, 5, 15, 0.65)"
        self.G = "rgba(10, 175, 85, 0.75)"
        self.B = "rgba(12, 13, 180, 0.15)"
        self.L = "rgba(221, 221, 221, 0.45)"

oldcolors = SeriesColors()
seriescolors = SeriesColorsAlpha()


"""
Some lambda-logic:

hascase(object, chr)
    -> True if the object has an attr named 'chr' REGARDLESS OF CASE.

hasallcaselist(object, str)
    -> a one-dimensional truth table corresponding to the evaluation of strings' charachter indexes.

hasallcase(object, str)
    -> True if the object as an attr named after EACH character in the string, REGARDLESS OF CASE.

getcase(object, chr)
    -> returns the attr named 'chr' REGARDLESS OF CASE.

getallcase(object, str)
    -> returns a list of values each corresponding to the result of accessing the an attr on the object named thus.

"""
hascase = lambda wtf, p: hasattr(wtf, str(p).upper()) or hasattr(wtf, str(p).lower())
hasallcaselist = lambda wtf, st: map(lambda p: hascase(wtf, p), list(st))
hasallcase = lambda wtf, sst: reduce(lambda l,r: l & r, hasallcaselist(wtf, sst), True)
getcase = lambda wtf, p: getattr(wtf, str(p).upper(), getattr(wtf, str(p).lower(), None))
getallcase = lambda wtf, st: map(lambda m: getcase(wtf, m), list(st))

"""
... in here, you see:

    hasallcase(dict, 'xyz')          VS.          hasallcase(dict, 'rgb')

is pretty significant.

"""


def itersubclasses(cls, _seen=None):
    """
    itersubclasses(cls) -- from http://code.activestate.com/recipes/576949/
    
    Generator over all subclasses of a given class, in depth first order.
    
    >>> list(itersubclasses(int)) == [bool]
    True
    >>> class A(object): pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B,C): pass
    >>> class E(D): pass
    >>> 
    >>> for cls in itersubclasses(A):
    ...     print(cls.__name__)
    B
    D
    E
    C
    >>> 
    >>> # get ALL (new-style) classes currently defined
    >>> [cls.__name__ for cls in itersubclasses(object)]
    ['type', ...'tuple', ...]
    
    """
    
    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None: _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError: # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub
