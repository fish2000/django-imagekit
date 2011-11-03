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

from cpython cimport bool

cimport numpy
import numpy
numpy.import_array()

from scipy import misc
from PIL import Image
import random

ctypedef numpy.uint32_t uint32_t

cdef int random_int(int top):
    return random.randint(0, top)

cdef extern from "processors.h":
    unsigned char adderror(int b, int e)
    unsigned char* threshold_matrix

cdef extern from "stdlib.h":
    int c_abs "abs"(int i)
    #int c_random "random"(int i)

cdef class Atkinsonify:
    
    cdef readonly float threshold
    cdef readonly object format
    cdef readonly object extension
    
    def __cinit__(self,
        int threshold = 128,
        format="PNG",
        extension="png"):
        
        self.threshold = threshold
        self.format = format
        self.extension = format.lower()
        
        for i from 0 <= i < 256:
            if i < self.threshold:
                threshold_matrix[i] = 0x00
            else:
                threshold_matrix[i] = 0xFF
    
    @cython.boundscheck(False)
    def process(self not None, pilimage not None, format not None, obj not None):
        #in_array = misc.fromimage(pilimage, flatten=True).astype(numpy.uint8)
        in_array = numpy.array(pilimage.convert("L"), dtype=numpy.uint8)
        
        atkinson(in_array)
        pilout = misc.toimage(in_array)
        return pilout, format

@cython.boundscheck(False)
@cython.wraparound(False)
def atkinson(numpy.ndarray[numpy.uint8_t, ndim=2, mode="c"] image_i not None):
    
    cdef int x, y, w, h, i
    cdef int err
    cdef unsigned char old, new
    
    w = image_i.shape[0]
    h = image_i.shape[1]
    
    for y from 0 <= y < h:
        for x from 0 <= x < w:
            old = image_i[x, y]
            new = threshold_matrix[old]
            err = (old - new) >> 3
            
            image_i[x, y] = new
            
            # x+1, y
            if x+1 < w:
                image_i[x+1, y] = adderror(image_i[x+1, y], err);
            
            # x+2, y
            if x+2 < w:
                image_i[x+2, y] = adderror(image_i[x+2, y], err);
            
            # x-1, y+1
            if x > 0 and y+1 < h:
                image_i[x-1, y+1] = adderror(image_i[x-1, y+1], err);
            
            # x, y+1
            if y+1 < h:
                image_i[x, y+1] = adderror(image_i[x, y+1], err);
            
            # x+1, y+1
            if x+1 < w and y+1 < h:
                image_i[x+1, y+1] = adderror(image_i[x+1, y+1], err);
            
            # x, y+2
            if y+2 < h:
                image_i[x, y+2] = adderror(image_i[x, y+2], err);


cdef class StentifordModel:
    
    @cython.boundscheck(False)
    @cython.wraparound(False)
    def distance(self,
        numpy.ndarray[numpy.uint32_t, ndim=1, mode="c"] matrix_a not None,
        numpy.ndarray[numpy.uint32_t, ndim=1, mode="c"] matrix_b not None):
        
        return numpy.sum(numpy.abs(matrix_a - matrix_b))
    
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
        
        return
        
    @cython.boundscheck(False)
    @cython.wraparound(False)
    cdef inline void rgb_to_hsv(self, float r=0.0, float g=0.0, float b=0.0, float h=0.0, float s=1, float v=1):
        """Convert RGB color space to HSV color space
        
        @param r: Red
        @param g: Green
        @param b: Blue
        return (h, s, v)
        """
        cdef float maxc, minc
        
        maxc = max(r, g, b)
        minc = min(r, g, b)
        colorMap = {
            id(r): 'r',
            id(g): 'g',
            id(b): 'b'
        }
        if colorMap[id(maxc)] == colorMap[id(minc)]:
            h = 0
        elif colorMap[id(maxc)] == 'r':
            h = 60.0 * ((g - b) / (maxc - minc)) % 360.0
        elif colorMap[id(maxc)] == 'g':
            h = 60.0 * ((b - r) / (maxc - minc)) + 120.0
        elif colorMap[id(maxc)] == 'b':
            h = 60.0 * ((r - g) / (maxc - minc)) + 240.0
        v = maxc
        if maxc == 0.0:
            s = 0.0
        else:
            s = 1.0 - (minc / maxc)
        
        #return (h, s, v)
        return
    
    cdef object random_neighborhood
    cdef int neighborhood_size
    
    cdef object possible_neighbors
    cdef object attention_model
    
    cdef int max_checks
    cdef int max_dist
    cdef int radius
    
    cdef int side
    cdef int cnt
    
    dt = numpy.uint32
    
    def __init__(self, *args, **kwargs):
        self.neighborhood_size = kwargs.pop('neighborhood_size', self.neighborhood_size)
        self.max_checks = kwargs.pop('max_checks', self.max_checks)
        self.max_dist = kwargs.pop('max_dist', self.max_dist)
        
        self.neighborhood_size = 3
        self.random_neighborhood = set(xrange(self.neighborhood_size))
        self.max_checks = 100
        self.max_dist = 40
        self.radius = 2
        self.side = 0
        
        super(StentifordModel, self).__init__(*args, **kwargs)
        random.seed()
        
        # compute possible neighbors with our params
        self.side = 2 * self.radius + 1
        
        cdef int i, j
        
        from_the_block = list()
        for i from self.radius*-1 <= i < self.radius+1:
            for j from self.radius*-1 <= j < self.radius+1:
                if j > 0 or i > 0:
                    from_the_block.append((i, j))
        
        self.possible_neighbors = numpy.array(from_the_block, dtype=self.dt)
    
    def ogle(self, pilimage):
        return self._ogle(numpy.array(pilimage.convert("RGB"), dtype=numpy.uint8), pilimage)
    
    cdef _ogle(self, numpy.ndarray[numpy.uint8_t, ndim=3, mode="c"] in_array, object pilimage):
        cdef int x, y, idx, randx, randy
        cdef bool match = True
        cdef numpy.ndarray xmatrix, ymatrix
        
        
        # initialize attention model matrix with the dimensions of our image,
        # loaded with zeroes:
        self.attention_model = numpy.array(
            [0] * (pilimage.size[0] * pilimage.size[1]),
            dtype=self.dt,
        ).reshape(*pilimage.size)
        
        # populate the matrix with per-pixel attention values
        #  from 0 <= y < 
        for x from self.radius <= x < pilimage.size[0]-self.radius:
            for y from self.radius <= y < pilimage.size[1]-self.radius:
                self.regentrify()
                
                xmatrix = numpy.array([(0,0,0)] * (pilimage.size[0] * pilimage.size[1]), dtype=self.dt)
                self.there_goes_the_neighborhood(x, y, in_array, xmatrix)
                
                for checks from 0 <= checks < self.max_checks:
                    randx = <int>((pilimage.size[0]-2*self.radius)+self.radius)
                    randy = <int>((pilimage.size[1]-2*self.radius)+self.radius)
                    
                    ymatrix = numpy.array([(0,0,0)] * (pilimage.size[0] * pilimage.size[1]), dtype=self.dt)
                    self.there_goes_the_neighborhood(
                        random_int(randx),
                        random_int(randy),
                        in_array, ymatrix,
                    )
                    
                    match = True
                    for idx from 0 <= idx < xmatrix.shape[0]:
                        if self.distance(xmatrix[idx], ymatrix[idx]) > self.max_dist:
                            match = False
                            break
                    
                    if not match:
                        self.attention_model[x, y] += 1
    
    cdef there_goes_the_neighborhood(self, int x, int y,
        numpy.ndarray[numpy.uint8_t, ndim=3, mode="c"] in_array,
        numpy.ndarray[numpy.uint32_t, ndim=2, mode="c"] out_array):
        """
        Retrieve a neighborhood of values around a given pixel in the source image.
        
        """
        out = list()
        cdef int denizen
        cdef int r, g, b
        cdef float h = 0.0, s = 0.0, v = 0.0
        
        for denizen in self.random_neighborhood:
            i_want_x = abs(x + self.possible_neighbors[denizen, 0])
            i_want_y = abs(y + self.possible_neighbors[denizen, 1])
            
            r, g, b = in_array[
                i_want_x < in_array.shape[0] and i_want_x or in_array.shape[0]-1,
                i_want_y < in_array.shape[1] and i_want_y or in_array.shape[1]-1,
            ]
            
            self.rgb_to_hsv(<float>r, <float>g, <float>b, h, s, v)
            
            out_array[denizen][0] = <uint32_t>h
            out_array[denizen][1] = <uint32_t>s
            out_array[denizen][2] = <uint32_t>v
        
        return out_array
    
    cdef regentrify(self):
        """
        Repopulate the random neighborhood array with random values,
        bounded by the size of possible_neighbors (which itself is
        derived from the algo's initial parameter values.)
        
        """
        cdef int possible_neighbors_shape
        
        self.random_neighborhood.clear()
        possible_neighbors_shape = self.possible_neighbors.shape[0]
        denizen = random_int(possible_neighbors_shape)
        
        if denizen == self.possible_neighbors.shape[0]:
            denizen -= 1
        
        self.random_neighborhood.add(denizen)
    
    @property
    def pilimage(self):
        """
        PIL image instance property containing the visualized analysis results.
        
        """
        #if hasattr(self, 'attention_model'):
        pilout = Image.new('RGB', self.attention_model.shape)
        for i in xrange(self.attention_model.shape[0]):
            for j in xrange(self.attention_model.shape[1]):
                pix = self.attention_model[i, j]
                compand = int((float(pix) / float(self.max_checks)) * 255.0)
                pilout.putpixel((i, j), (compand, compand, compand))
        return pilout
        #return None
    

