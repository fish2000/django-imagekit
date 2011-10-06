
cimport numpy
from scipy import misc

cdef extern from "processors.h":
    unsigned char adderror(char b, int e)


cdef class Atkinsonify:
    
    cdef readonly double threshold
    cdef unsigned char threshold_matrix[255]
    
    def __cinit__(self, float threshold=128.0):
        self.threshold = threshold
        
        for i in xrange(255):
            self.threshold_matrix[i] = int(i/self.threshold)
    
    def process(self, pilimage, format, obj):
        in_array = misc.fromimage(pilimage, flatten=True)
        #out_array = numpy.zeros(in_array.shape, dtype=numpy.uint8)
        
        self.atkinson(in_array)
        pilout = misc.toimage(in_array)
        
        return pilout, format
    
    def atkinson(self, numpy.ndarray[numpy.uint8_t, ndim=2, mode="c"] image_i not None):
        
        cdef int w, h, i, err
        cdef unsigned char old, new
        
        w = image_i.shape[0]
        h = image_i.shape[1]
        
        for y in xrange(h):
            for x in xrange(w):
                old = image_i[x, y]
                new = self.threshold_matrix[old]
                err = (old - new) >> 3
                
                image_i[x, y] = adderror(image_i[x, y], err)
                
                for nxy in [(x+1, y), (x+2, y), (x-1, y+1), (x, y+1), (x+1, y+1), (x, y+2)]:
                    try:
                        image_i[nxy[0], nxy[1]] = image_i[nxy[0], nxy[1]] + err
                    except IndexError:
                        pass
    
                