#!/usr/bin/env python
# encoding: utf-8
"""
tests.py

Tests for django-imagekit.

Created by FI$H 2000 on 2011-09-01.
Copyright (c) 2011 Objects In Space And Time, LLC. All rights reserved.

"""

import os, tempfile, shutil, logging, types, unittest
from django.conf import settings
import imagekit.schmettings
imagekit.schmettings.__dict__.update({
    'NOSE_ARGS': ['--rednose', '--nocapture', '--nologcapture'],
    'SQ_ASYNC': True,
})

# '--with-profile', '--profile-sort=cumulative'

if not settings.configured:
    settings.configure(**imagekit.schmettings.__dict__)
    import logging.config
    logging.config.dictConfig(settings.LOGGING)

rp = None

if __name__ == '__main__':
    
    if settings.SQ_ASYNC:
        import subprocess, signalqueue
        rp = subprocess.Popen(['redis-server',
            "%s" % os.path.join(os.path.dirname(signalqueue.__file__), 'etc', 'redis.conf')],
            stdout=subprocess.PIPE)
        print "*** Starting test Redis server instance (pid = %s)" % rp.pid
    
    from django.core.management import call_command
    
    '''
    call_command('test', 'imagekit.tests:IKTest',
        interactive=False, traceback=True, verbosity=2)
    '''
    
    call_command('test', 'imagekit',
        interactive=False, traceback=True, verbosity=2)
    
    if rp is not None:
        import signal
        print "*** Shutting down test Redis server instance (pid = %s)" % rp.pid
        os.kill(rp.pid, signal.SIGKILL)
    
    print ""
    '''
    call_command('test', 'imagekit.tests:IKSyncTest',
        interactive=False, traceback=True, verbosity=2)
    '''
    
    tempdata = imagekit.schmettings.tempdata
    print "*** Deleting test data: %s" % tempdata
    shutil.rmtree(tempdata)
    
    #print ""
    #import sys
    #sys.exit(0)

from django.test import TestCase
#from django.test.utils import override_settings as override

from django.core.files.base import ContentFile
from django.db import models

from imagekit import processors
from imagekit.models import ImageModel, ImageWithMetadata
from imagekit.models import _storage
from imagekit.specs import ImageSpec
from imagekit.lib import Image, ICCProfile, IK_ROOT

class ResizeToWidth(processors.Resize):
    width = 100

class ResizeToHeight(processors.Resize):
    height = 100

class ResizeToFit(processors.Resize):
    width = 100
    height = 100

class ResizeCropped(ResizeToFit):
    crop = ('center', 'center')

class SmartCropped(processors.SmartCrop):
    width = 100
    height = 100

class SmarterCropped(processors.SmartCrop):
    width = 200
    height = 200

class TransformICC(processors.ICCTransform):
    source = ICCProfile(os.path.join(IK_ROOT, "icc/sRGB-IEC61966-2-1.icc"))
    destination = ICCProfile(os.path.join(IK_ROOT, "icc/adobeRGB-1998.icc"))

class ProofICC(processors.ICCProofTransform):
    source = ICCProfile(os.path.join(IK_ROOT, "icc/sRGB-IEC61966-2-1.icc"))
    destination = ICCProfile(os.path.join(IK_ROOT, "icc/adobeRGB-1998.icc"))
    proof = ICCProfile(os.path.join(IK_ROOT, "icc/CMYK-USWebCoatedSWOP-2.icc"))

class Atkinsonizer(processors.Atkinsonify):
    pass

class NeuQuantizer(processors.NeuQuantize):
    pass

class Stentifordizer(processors.Stentifordize):
    max_checks = 10

class Trimmer(processors.Trim):
    pass


class TestResizeToWidth(ImageSpec):
    access_as = 'to_width'
    processors = [ResizeToWidth]

class TestResizeToHeight(ImageSpec):
    access_as = 'to_height'
    processors = [ResizeToHeight]

class TestResizeCropped(ImageSpec):
    access_as = 'cropped'
    processors = [ResizeCropped]

class TestSmartCropped(ImageSpec):
    access_as = 'smartcropped'
    processors = [ResizeToHeight, SmartCropped]

class TestSmarterCropped(ImageSpec):
    access_as = 'smartercropped'
    processors = [SmarterCropped]

class TestICCTransform(ImageSpec):
    #pre_cache = True
    access_as = 'icctrans'
    processors = [TransformICC]

class TestICCProof(ImageSpec):
    #pre_cache = True
    access_as = 'iccproof'
    processors = [ProofICC]

class TestAtkinsonizer(ImageSpec):
    access_as = 'atkinsonized'
    processors = [SmarterCropped, processors.Atkinsonify]
    #processors = [processors.Atkinsonify]

class TestAtkinsonizerSlow(ImageSpec):
    access_as = 'atkinsonized_slow'
    processors = [SmarterCropped, processors.Atkinsonify_YoDogg]
    #processors = [processors.Atkinsonify]

class TestNeuQuantizer(ImageSpec):
    access_as = 'neuquantized'
    processors = [ResizeToHeight, SmartCropped, NeuQuantizer]

class TestStentifordizer(ImageSpec):
    access_as = 'stentifordized'
    processors = [SmarterCropped, Stentifordizer]

class TestTrimmer(ImageSpec):
    access_as = 'trimmed'
    processors = [Trimmer]

class TestImage(ImageModel):
    """
    Minimal ImageModel class for testing.
    
    """
    class Meta:
        app_label = 'imagekit'
        db_table = 'imagekit_testimage'
    
    class IKOptions:
        spec_module = 'imagekit.tests'
        storage = _storage
    
    image = models.ImageField(upload_to='testimages', storage=_storage)


class TestImageM(ImageWithMetadata):
    """
    Minimal ImageWithMetadata class for testing.
    
    """
    class Meta:
        app_label = 'imagekit'
        db_table = 'imagekit_testimagem'
    
    class IKOptions:
        spec_module = 'imagekit.tests'
        storage = _storage
    
    image = models.ImageField(upload_to='testmimages', storage=_storage)


def get_image():
    import StringIO
    
    if get_image.imgstr is None:
        import urllib2, random
        urls = [
            'http://ost2.s3.amazonaws.com/images/_uploads/IfThen_Detail_Computron_Orange_2to3_010.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/2805163544_1321ee6d30_o.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/IfThen_Detail_Computron_Silver_2to3_010.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/Josef_Muller_Brockmann_Detail_Lights_2to3_000.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/P4141870.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/After_The_Quake_Detail_Text_2to3_000.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/P4141477.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/P4141469.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/IMG_1310.jpg',
            'http://ost2.s3.amazonaws.com/images/_uploads/P4141472.jpg',
        ]
        random.seed()
        imgurl = random.choice(urls)
        print "Loading image: %s" % imgurl
        get_image.imgstr = urllib2.urlopen(imgurl).read()
    
    img = Image.open(StringIO.StringIO(get_image.imgstr)).crop((0, 0, 800, 600))
    tmp = tempfile.TemporaryFile()
    img.save(tmp, 'JPEG')
    tmp.seek(0)
    
    #get_image.imgstr = None
    return tmp

get_image.imgstr = None

class TestMethodReferenceFixerUpper(type):
    def __init__(cls, name, bases, attrs):
        basefuncs = dict(filter(lambda attr: type(attr[1]) in (types.FunctionType, types.MethodType, types.UnboundMethodType) and (not attr[0].lower().startswith('setup')), attrs.items()))
        for funcname, func in basefuncs.items():
            if hasattr(func, 'im_class'):
                func.im_class = cls
        type.__init__(cls, name, bases, attrs)

class TestCopier(TestMethodReferenceFixerUpper):
    def __new__(cls, name, bases, attrs):
        from copy import deepcopy
        
        for base in bases:
            basefuncs = dict(filter(lambda attr: type(attr[1]) in (types.FunctionType, types.MethodType) and (not attr[0].lower().startswith('setup')), base.__dict__.items()))
            
            #print "--- Copying %s test funcs from base %s" % (len(basefuncs), base.__name__)
            for funcname, func in basefuncs.items():
                attrs[funcname] = deepcopy(func)
            if 'tearDown' in base.__dict__:
                attrs['tearDown'] = deepcopy(base.__dict__.get('tearDown'))
        
        return type(name, (TestCase,), attrs)

class IKTest(TestCase):
    """
    Base TestCase class.
    
    """
    
    __metaclass__ = TestMethodReferenceFixerUpper
    __test__ = True
    
    def __init__(self, *args, **kwargs):
        basefuncs = dict(filter(lambda attr: type(attr[1]) in (types.UnboundMethodType,) and (not attr[0].lower().startswith('setup')), self.__dict__.items()))
        for funcname, func in basefuncs.items():
            if hasattr(func, 'im_class'):
                func.im_class = type(self.__class__.__name__, self.__class__, dict(self.__class__.__dict__))
        super(self.__class__, self).__init__(*args, **kwargs)
    
    def generate_image(self):
        tmp = tempfile.TemporaryFile()
        Image.new('RGB', (800, 600)).save(tmp, 'JPEG')
        tmp.seek(0)
        return tmp
    
    def get_image(self):
        return get_image()
    
    def runTest(self):
        return True
    
    def setUp(self):
        print ""
        
        # dispatch all signals asynchronously
        with self.settings(SQ_ASYNC=True, SQ_RUNMODE='SQ_ASYNC_REQUEST'):
            import signalqueue
            queues = signalqueue.worker.backends.ConnectionHandler(settings.SQ_QUEUES, 4)
            signalqueue.worker.queues = queues
            signalqueue.rediscover()
            
            # image instance for testing
            self.p = TestImage()
            try:
                img = self.get_image()
            except (IOError, AttributeError, ValueError), err:
                print "~~~ Exception thrown DURING SETUP by IKTest.get_image(): %s" % err
                img = self.generate_image()
            self.p.save_image('test.jpeg', ContentFile(img.read()))
            self.p.save()
            img.close()
    
    def test_save_image(self):
        img = self.generate_image()
        
        path = self.p.image.name
        self.p.save_image('test2.jpeg', ContentFile(img.read()))
        self.failIf(self.p._ik.storage.exists(path))
        
        path = self.p.image.name
        img.seek(0)
        self.p.save_image('test.jpeg', ContentFile(img.read()))
        self.failIf(self.p._ik.storage.exists(path))
        
        img.close()
    
    def test_icc_transform(self):
        self.assertTrue(self.p.icctrans.url is not None)
        self.assertEqual(self.p.image.width, self.p.icctrans.width)
        self.assertEqual(self.p.image.height, self.p.icctrans.height)
    
    def test_icc_proof_transform(self):
        self.assertTrue(self.p.iccproof.url is not None)
        self.assertEqual(self.p.image.width, self.p.iccproof.width)
        self.assertEqual(self.p.image.height, self.p.iccproof.height)
    
    def test_imagewithmetadata(self):
        pm = TestImageM()
        try:
            img = self.get_image()
        except (IOError, AttributeError, ValueError), err:
            print "&&& Exception thrown WHILE TESTING IMAGEWITHMETADATA by IKTest.get_image(): %s" % err
            img = self.generate_image()
        
        pm.save_image('mtest.jpg', ContentFile(img.read()))
        img.close()
        
        self.assertEqual(pm.image.width, 800)
        self.assertEqual(pm.image.height, 600)
        self.assertEqual(pm.cropped.width, 100)
        self.assertEqual(pm.cropped.height, 100)
        self.assertEqual(pm.smartcropped.width, 100)
        self.assertEqual(pm.smartcropped.height, 100)
        self.assertEqual(pm.smartercropped.width, pm.atkinsonized.width)
        self.assertEqual(pm.smartercropped.height, pm.atkinsonized.height)
        
        pth = pm.image.name
        pm.save()
        pm.delete(clear_cache=True)
        
        self.failIf(pm._ik.storage.exists(pth))
    
    def test_setup(self):
        self.assertEqual(self.p.image.width, 800)
        self.assertEqual(self.p.image.height, 600)
    
    def test_to_width(self):
        self.assertEqual(self.p.to_width.width, 100)
        self.assertEqual(self.p.to_width.height, 75)
    
    def test_to_height(self):
        self.assertEqual(self.p.to_height.width, 133)
        self.assertEqual(self.p.to_height.height, 100)
    
    def test_crop(self):
        self.assertEqual(self.p.cropped.width, 100)
        self.assertEqual(self.p.cropped.height, 100)
    
    def test_smartcrop(self):
        self.assertEqual(self.p.smartcropped.width, 100)
        self.assertEqual(self.p.smartcropped.height, 100)
    
    def test_atkinsonizer(self):
        self.assertEqual(self.p.smartercropped.width, self.p.atkinsonized.width)
        self.assertEqual(self.p.smartercropped.height, self.p.atkinsonized.height)
        self.assertTrue(self.p.atkinsonized.name.lower().endswith('.png'))
    
    def test_atkinsonizer_slow(self):
        self.assertEqual(self.p.smartercropped.width, self.p.atkinsonized_slow.width)
        self.assertEqual(self.p.smartercropped.height, self.p.atkinsonized_slow.height)
        self.assertTrue(self.p.atkinsonized_slow.name.lower().endswith('.png'))
    
    def test_neuquantizer(self):
        self.assertTrue(self.p.neuquantized.url is not None)
    
    def _test_stentifordizer(self):
        self.assertTrue(self.p.stentifordized.url is not None)
    
    def test_trimmer(self):
        self.assertTrue(self.p.trimmed.url is not None)
        self.assertTrue(self.p.trimmed.width <= self.p.image.width)
        self.assertTrue(self.p.trimmed.height <= self.p.image.height)
    
    def test_url(self):
        self.assertEqual(
            self.p.to_width.url,
            _storage.url(os.path.join(self.p._ik.cache_dir, self.p.image.name.replace('.jpeg', '_to_width.jpeg'))),
        )
    
    def tearDown(self):
        # make sure image file is deleted
        pth = self.p.image.name
        self.p.delete(clear_cache=True)
        self.failIf(_storage.exists(pth))

class IKSyncTest(IKTest):
    
    __metaclass__ = TestCopier
    __test__ = True
    
    def setUp(self):
        print ""
        
        # dispatch all signals synchronously
        from django.conf import settings
        settings.SQ_RUNMODE = 'SQ_SYNC'
        with self.settings(SQ_ASYNC=False, SQ_RUNMODE='SQ_SYNC'):
            import signalqueue
            queues = signalqueue.worker.backends.ConnectionHandler(settings.SQ_QUEUES, 1)
            signalqueue.worker.queues = queues
            signalqueue.rediscover()
            
            # image instance for testing
            self.p = TestImage()
            try:
                img = self.get_image()
            except (IOError, AttributeError, ValueError), err:
                print "~~~ Exception thrown DURING SETUP by IKTest.get_image(): %s" % err
                img = self.generate_image()
            self.p.save_image('test.jpeg', ContentFile(img.read()))
            self.p.save()
            img.close()

def suite():
    
    testcases = []
    for test in (IKTest, IKSyncTest):
        testcases.append(unittest.TestLoader().loadTestsFromTestCase(test))
    
    return unittest.TestSuite(testcases)
