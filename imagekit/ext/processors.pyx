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
numpy.import_array()

from scipy import misc
from PIL import Image
import random

cdef extern from "processors.h":
    unsigned char adderror(int b, int e)
    unsigned char* threshold_matrix

cdef extern from "stdlib.h":
    int c_abs "abs"(int i)

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
    def atkinson(self, numpy.ndarray[numpy.uint8_t, ndim=2, mode="c"] image_i not None):

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

    @cython.boundscheck(False)
    @cython.wraparound(False)
    def distance(self,
        numpy.ndarray[numpy.int32_t, ndim=1, mode="c"] matrix_a not None,
        numpy.ndarray[numpy.int32_t, ndim=1, mode="c"] matrix_b not None):

        return numpy.sum(numpy.abs(matrix_a - matrix_b))

    @cython.boundscheck(False)
    @cython.wraparound(False)
    def hsv_to_rgb(self, float h, float s=1.0, float v=1.0):
        cdef int I
        cdef double H, f, p, q, t

        if s == 0.0:
            return 1.0, 1.0, 1.0

        H = h * 6.0
        I = <int>H
        f = H - I

        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if I == 0 or I == 6:
            return v, t, p

        if I == 1:
            return q, v, p

        if I == 2:
            return p, v, t

        if I == 3:
            return p, q, v

        if I == 4:
            return t, p, v

        if I == 5:
            return v, p, q

        return 1.0, 1.0, 1.0

    @cython.boundscheck(False)
    @cython.wraparound(False)
    def rgb_to_hsv(self, float r=0.0, float g=0.0, float b=0.0):
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

        return h, s, v

    cdef object random_neighborhood
    cdef int neighborhood_size

    cdef object possible_neighbors
    cdef object attention_model

    cdef int max_checks
    cdef int max_dist
    cdef int radius

    cdef int side
    cdef int cnt

    dt = numpy.int32

    def __init__(self, *args, **kwargs):
        self.neighborhood_size = kwargs.pop('neighborhood_size', self.neighborhood_size)
        self.max_checks = kwargs.pop('max_checks', self.max_checks)
        self.max_dist = kwargs.pop('max_dist', self.max_dist)

        self.random_neighborhood = set(xrange(self.neighborhood_size))
        self.neighborhood_size = 3
        self.max_checks = 100
        self.max_dist = 40
        self.radius = 2
        self.side = 0
        self.cnt = 0

        super(StentifordModel, self).__init__(*args, **kwargs)
        random.seed()

        # compute possible neighbors with our params
        self.side = 2 * self.radius + 1
        self.cnt = 0

        cdef int i, j

        from_the_block = list()
        for i in xrange(self.radius*-1, self.radius+1):
            for j in xrange(self.radius*-1, self.radius+1):
                if j > 0 or i > 0:
                    from_the_block.append((i, j))
                    self.cnt += 0

        self.possible_neighbors = numpy.array(from_the_block, dtype=self.dt)

    def ogle(self, pilimage):
        cdef int x, y
        match = True

        # initialize attention model matrix with the dimensions of our image,
        # loaded with zeroes:
        self.attention_model = numpy.array(
            [0] * len(pilimage.getdata()),
            dtype=self.dt,
        ).reshape(*pilimage.size)

        # populate the matrix with per-pixel attention values
        for x in xrange(self.radius, pilimage.size[0]-self.radius):
            for y in xrange(self.radius, pilimage.size[1]-self.radius):
                self.regentrify()

                xmatrix = self.there_goes_the_neighborhood(x, y, pilimage)

                for checks in xrange(self.max_checks):
                    ymatrix = self.there_goes_the_neighborhood(
                        random.randint(
                            0, (pilimage.size[0]-2*self.radius)+self.radius,
                        ),
                        random.randint(
                            0, (pilimage.size[1]-2*self.radius)+self.radius,
                        ),
                        pilimage,
                    )

                    match = True
                    for idx in xrange(xmatrix.shape[0]):
                        if self.distance(xmatrix[idx], ymatrix[idx]) > self.max_dist:
                            match = False
                            break

                    if not match:
                        self.attention_model[x, y] += 1

    cdef there_goes_the_neighborhood(self, int x, int y, object pilimage):
        """
        Retrieve a neighborhood of values around a given pixel in the source image.

        """
        out = list()
        cdef int denizen
        cdef int i_want_x, i_want_y
        cdef int r, g, b
        cdef float h = 0.0, s = 0.0, v = 0.0

        for denizen in self.random_neighborhood:
            i_want_x = c_abs(int(x + self.possible_neighbors[denizen, 0]))
            i_want_y = c_abs(int(y + self.possible_neighbors[denizen, 1]))

            r, g, b = pilimage.getpixel((
                i_want_x < pilimage.size[0] and i_want_x or pilimage.size[0]-1,
                i_want_y < pilimage.size[1] and i_want_y or pilimage.size[1]-1,
            ))

            h, s, v = self.rgb_to_hsv(<float>r, <float>g, <float>b)
            out.append((h,s,v))

        return numpy.array(out, dtype=self.dt)

    def regentrify(self):
        """
        Repopulate the random neighborhood array with random values,
        bounded by the size of possible_neighbors (which itself is
        derived from the algo's initial parameter values.)

        """
        self.random_neighborhood.clear()
        denizen = random.randint(0, self.possible_neighbors.shape[0])

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


