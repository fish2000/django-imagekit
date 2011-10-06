<<<<<<< HEAD
# Required PIL classes may or may not be available from the root namespace
# depending on the installation method used.
try:
    import Image
    import ImageFile
    import ImageFilter
    import ImageEnhance
    import ImageColor
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
        from PIL import ImageColor
    except ImportError:
        raise ImportError('ImageKit was unable to import the Python Imaging Library. Please confirm it`s installed and available on your current Python path.')
=======

# Required PIL classes may or may not be available from the root namespace
# depending on the installation method used.
try:
    import Image
    import ImageFile
    import ImageFilter
    import ImageEnhance
    import ImageColor
    
    import ImageCms
except ImportError:
    try:
        from PIL import Image
        from PIL import ImageFile
        from PIL import ImageFilter
        from PIL import ImageEnhance
        from PIL import ImageColor
        
        from PIL import ImageCms
        
    except ImportError:
        raise ImportError('ImageKit was unable to import the Python Imaging Library. Please confirm it`s installed and available on your current Python path.')


"""
it ain't where you from,
it's where you at.
"""
import os
IK_ROOT = os.path.dirname(os.path.realpath(__file__))




>>>>>>> a543904... Initial commit of F2K ImageKit fork.
