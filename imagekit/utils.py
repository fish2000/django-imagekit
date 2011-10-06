""" ImageKit utility functions """

import tempfile

def img_to_fobj(img, format, **kwargs):
    tmp = tempfile.TemporaryFile()
    
    #preserve transparency if the image is in Pallette (P) mode
    if img.mode == 'P':
        kwargs['transparency'] = len(img.split()[-1].getcolors())
    else:
        img.convert('RGB')
    
    img.save(tmp, format, **kwargs)
    tmp.seek(0)
    return tmp
<<<<<<< HEAD
=======


def pil_for_lut(lut):
    """
    make a PIL image from an RGB LUT of format:
    [
        (r,g,b),
        (r,g,b),
        ...
    ]
    where r, g, b are 0-255. 
    
    """
    from imagekit.lib import Image, ImageCms
    
    outlut = Image.new('RGB', (1, len(lut)+2))
    outpix = outlut.load()
    
    for p in range(len(lut)):
        outpix[0,p] = lut[p]
    
    return outlut
>>>>>>> 319667b... Refactored lcms-based profile/proof transform processors and added base classes for spec/processor chains that yield something other than an image (e.g. a numpy matrix for example).
