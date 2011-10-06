#!/usr/bin/env python
# encoding: utf-8
# cython: profile=True
"""
processors.pyx

Cython alternative implementations of some of the ImageProcessors from imagekit.processors.

Created by FI$H 2000 on 2011-10-06.
Copyright (c) 2011 Objects In Space And Time, LLC. All rights reserved.

"""
import cython

cimport numpy
import numpy
from scipy import misc

cdef extern from "processors.h":
    unsigned char adderror(int b, int e)
    unsigned char* threshold_matrix


cdef class Atkinsonify:
    
    cdef readonly float threshold
    cdef readonly object format
    cdef readonly object extension
    
    def __cinit__(self,
        float threshold=128.0,
        format="PNG",
        extension="png"):
        
        self.threshold = threshold
        self.format = format
        self.extension = format.lower()
        
        for i in xrange(255):
            threshold_matrix[i] = int(i/self.threshold)
    
    def process(self, pilimage, format, obj):
        in_array = misc.fromimage(pilimage, flatten=True).astype(numpy.uint8)
        self.atkinson(in_array)
        pilout = misc.toimage(in_array)
        return pilout, format
    
    @cython.boundscheck(False)
    cdef inline void atkinson(self, numpy.ndarray[numpy.uint8_t, ndim=2, mode="c"] image_i):
        
        cdef int x, y, w, h, i, err
        cdef unsigned char old, new
        
        w = image_i.shape[0]
        h = image_i.shape[1]
        
        for y in xrange(h):
            for x in xrange(w):
                old = image_i[x, y]
                new = threshold_matrix[old]
                err = (old - new) >> 3
                
                image_i[x, y] = adderror(image_i[x, y], err)
                
                for nxy in [(x+1, y), (x+2, y), (x-1, y+1), (x, y+1), (x+1, y+1), (x, y+2)]:
                    try:
                        image_i[nxy[0], nxy[1]] = (image_i[nxy[0], nxy[1]] + err)
                    except IndexError:
                        pass
    
                