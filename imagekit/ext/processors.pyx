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
    
    @cython.boundscheck(False)
    def process(self not None, pilimage not None, format not None, obj not None):
        in_array = misc.fromimage(pilimage, flatten=True).astype(numpy.uint8)
        self.atkinson(in_array)
        pilout = misc.toimage(in_array)
        return pilout, format
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline void atkinson(self, numpy.ndarray[numpy.uint8_t, ndim=2, mode="c"] image_i):
        
        cdef int x, y, w, h, i
        cdef int err
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


cdef class StentifordModel:
    
    cdef inline void distance(self,
        numpy.ndarray[numpy.uint32_t, ndim=2, mode="c"] matrix_a,
        numpy.ndarray[numpy.uint32_t, ndim=2, mode="c"] matrix_b,
        numpy.ndarray[numpy.uint32_t, ndim=2, mode="c"] matrix_o):
        
        matrix_o = numpy.sum(numpy.abs(matrix_a - matrix_b))
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline void hsv_to_rgb(self, float h, float s=1, float v=1, float r=0.0, float g=0.0, float b=0.0):
        cdef int I
        cdef double H, f, p, q, t
        
        if s == 0.0:
            r = v
            g = v
            b = v
            return
        
        H = h * 6.0
        I = <int>H
        f = H - I
        
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))
        
        if I == 0 or I == 6:
            #return v, t, p
            r = v
            g = t
            b = p
            return
        
        if I == 1:
            #return q, v, p
            r = q
            g = v
            b = p
            return
        
        if I == 2:
            #return p, v, t
            r = p
            g = v
            b = t
            return
        
        if I == 3:
            #return p, q, v
            r = p
            g = q
            b = v
            return
        
        if I == 4:
            #return t, p, v
            r = t
            g = p
            b = v
            return
        
        if I == 5: 
            #return v, p, q
            r = v
            g = p
            b = q
            return
    

                