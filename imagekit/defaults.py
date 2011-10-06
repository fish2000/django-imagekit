""" Default ImageKit configuration """

from imagekit import processors
from imagekit.spec import ImageSpec

class ResizeThumbnail(processors.Resize):
    width = 100
    height = 50
    crop = True

class EnhanceSmall(processors.Adjustment):
    contrast = 1.2
    sharpness = 1.1

class SampleReflection(processors.Reflection):
    size = 0.5
    background_color = "#000000"

class PNGFormat(processors.Format):
    format = 'PNG'
    extension = 'png'
