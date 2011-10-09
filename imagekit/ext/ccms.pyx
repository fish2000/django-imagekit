#!/usr/bin/env python
# encoding: utf-8
# cython: profile=True
"""

ccms.pyx

The cousin of little-cms: COLOSSAL-CMS.

Created by FI$H 2000 on 2011-10-06.
Copyright (c) 2011 Objects In Space And Time, LLC. All rights reserved.

"""

cdef extern from "lcms2.h":
    ctypedef float cmsFloat32Number
    ctypedef double cmsFloat64Number
    ctypedef unsigned int cmsUInt16Number
    ctypedef int cmsInt16Number
    ctypedef unsigned long cmsUInt32Number
    
    ctypedef struct cmsCIEXYZ:
        cmsFloat64Number X
        cmsFloat64Number Y
        cmsFloat64Number Z
    
    ctypedef void* cmsContext
    ctypedef void* cmsHANDLE
    ctypedef void* cmsHPROFILE
    ctypedef void* cmsHTRANSFORM
    
    ctypedef struct cmsICCMeasurementConditions:
        cmsUInt32Number Observer
        cmsCIEXYZ Backing
        cmsUInt32Number Geometry
        cmsFloat64Number Flare
        cmsUInt32Number IlluminantType



