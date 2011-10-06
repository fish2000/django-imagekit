import os, random, hashlib, math
import cStringIO as StringIO
from datetime import datetime
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q
from django.db.models.base import ModelBase
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
#from django.utils.html import conditional_escape as escape
from django.utils.translation import ugettext_lazy as _
from colorsys import rgb_to_hls, hls_to_rgb

from delegate import DelegateManager, delegate
from imagekit import signals as iksignals
from imagekit import specs
from imagekit.lib import *
from imagekit.options import Options
from imagekit.ICCProfile import ICCProfile
from imagekit.utils import logg, hexstr
from imagekit.utils import itersubclasses
from imagekit.utils import icchash as icchasher
from imagekit.utils.memoize import memoize
from imagekit.modelfields import ICCField, ICCHashField, RGBColorField
from imagekit.modelfields import ICCDataField, ICCMetaField, EXIFMetaField
from imagekit.modelfields import ImageHashField

# Modify image file buffer size.
ImageFile.MAXBLOCK = getattr(settings, 'PIL_IMAGEFILE_MAXBLOCK', 256 * 2 ** 10)

try:
    _storage = getattr(settings, 'IK_STORAGE', None)()
except:
    _storage = FileSystemStorage()
else:
    if not _storage:
        _storage = FileSystemStorage()

# attempt to load haystack
try:
    from haystack.query import SearchQuerySet
except (ImportError, ImproperlyConfigured):
    HAYSTACK = False
else:
    HAYSTACK = True


# Choice tuples for specifying the crop origin.
# These are provided for convenience.
CROP_HORZ_CHOICES = (
    (0, _('left')),
    (1, _('center')),
    (2, _('right')),
)

CROP_VERT_CHOICES = (
    (0, _('top')),
    (1, _('center')),
    (2, _('bottom')),
)


class ImageModelBase(ModelBase):
    """
    ImageModel metaclass
    
    This metaclass parses IKOptions and loads any ImageSpecs it can find in 'spec_module'.
    
    """
    def __init__(cls, name, bases, attrs):
        super(ImageModelBase, cls).__init__(name, bases, attrs)
        parents = [b for b in bases if isinstance(b, ImageModelBase)]
        if not parents:
            return
        
        user_opts = getattr(cls, 'IKOptions', None)
        opts = Options(user_opts)
        
        if opts.spec_module:
            try:
                module = __import__(opts.spec_module,  {}, {}, [''])
            except ImportError:
                raise ImportError('Unable to load imagekit config module: %s' % opts.spec_module)
            
            for spec in module.__dict__.values():
                if isinstance(spec, type) and not spec == specs.ImageSpec:
                    if issubclass(spec, specs.Spec):
                        opts.specs.update({ spec.name(): spec })
        
        # Options.contribute_to_class() won't work unless you do both of these. But... why?
        setattr(cls, '_ik', opts)
        cls.add_to_class('_ik', opts)


class ImageModel(models.Model):
    """
    Abstract base class implementing all core ImageKit functionality
    
    Subclasses of ImageModel are augmented with accessors for each defined
    image specification and can override the inner IKOptions class to customize
    storage locations and other options.
    
    """
    __metaclass__ = ImageModelBase
    
    class Meta:
        abstract = True
    
    class IKOptions:
        storage = _storage
    
    @property
    def _imgfield(self):
        return getattr(self, self._ik.image_field)
    
    @property
    def _storage(self):
        return getattr(self._ik, 'storage')
    
    @property
    @memoize
    def pilimage(self):
        if self.pk:
            if self._imgfield.name:
                return Image.open(self._storage.open(self._imgfield.name))
        return None
    
    def _dominant(self):
        return self.pilimage.quantize(1).convert('RGB').getpixel((0, 0))
    
    def _mean(self):
        return ImageStat.Stat(self.pilimage.convert('RGB')).mean
    
    def _average(self):
        return self.pilimage.convert('RGB').resize((1, 1), Image.ANTIALIAS).getpixel((0, 0))
    
    def _median(self):
        return reduce((lambda x,y: x[0] > y[0] and x or y), self.pilimage.convert('RGB').getcolors(self.pilimage.size[0] * self.pilimage.size[1]))
    
    def _topcolors(self, numcolors=3):
        if self.pilimage:
            colors = self.pilimage.convert('RGB').getcolors(self.pilimage.size[0] * self.pilimage.size[1])
            fmax = lambda x,y: x[0] > y[0] and x or y
            out = []
            out.append(reduce(fmax, colors))
            for i in range(1, numcolors):
                out.append(reduce(fmax, filter(lambda x: x not in out, colors)))
            return out
        return []
    
    def topsat(self, samplesize=10):
        try:
            return "#" + "".join(map(lambda x: "%02X" % int(x*255),
                map(lambda x: hls_to_rgb(x[0], x[1], x[2]), [
                    reduce(lambda x,y: x[2] > y[2] and x or y,
                        map(lambda x: rgb_to_hls(float(x[1][0])/255, float(x[1][1])/255, float(x[1][2])/255), self._topcolors(samplesize)))
                ])[0]
            ))
        except TypeError:
            return ""
    
    def dominanthex(self):
        return hexstr(self._dominant())
    
    def meanhex(self):
        m = self._mean()
        if len(m) == 3:
            return hexstr((int(m[0]), int(m[1]), int(m[2])))
        return hexstr((int(m[0]), int(m[0]), int(m[0])))
    
    def averagehex(self):
        return hexstr(self._average())
    
    def medianhex(self):
        return hexstr(self._median()[1])
    
    def tophex(self, numcolors=3):
        return [hexstr(tc[1]) for tc in self._topcolors(numcolors)]
    
    def save_image(self, name, image, save=True, replace=True):
        if hasattr(image, 'read'):
            data = image.read()
        else:
            data = image
        
        if self._imgfield and replace:
            self._imgfield.delete(save=False)
        
        content = ContentFile(data)
        self._imgfield.save(name, content, save=save)
    
    def save(self, *args, **kwargs):
        is_new_object = self._get_pk_val() is None
        clear_cache = kwargs.pop('clear_cache', False)
        
        super(ImageModel, self).save(*args, **kwargs)
        
        if is_new_object and self._imgfield:
            clear_cache = False
        
        if clear_cache:
            iksignals.clear_cache.send_now(sender=self.__class__, instance=self)
        
        #logg.info("About to send the pre_cache signal...")
        return iksignals.pre_cache.send_now(sender=self.__class__, instance=self)
    
    def delete(self, *args, **kwargs):
        clear_cache = kwargs.pop('clear_cache', False)
        if clear_cache:
            iksignals.clear_cache.send_now(sender=self.__class__, instance=self)
            self._imgfield.delete()
        super(ImageModel, self).delete(*args, **kwargs)
    
    def clear_cache(self, **kwargs):
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)
        iksignals.clear_cache.send_now(sender=self.__class__, instance=self)


class ImageWithMetadataQuerySet(models.query.QuerySet):
    
    def __init__(self, *args, **kwargs):
        super(ImageWithMetadataQuerySet, self).__init__(*args, **kwargs)
        random.seed()
    
    @delegate
    def rnd(self):
        return random.choice(self.all())
    
    @delegate
    def with_profile(self):
        return self.filter(icc__isnull=False)
    
    @delegate
    def with_exif(self):
        return self.filter(exif__isnull=False)
    
    @delegate
    def matching_profile(self, icc=None, hsh=None):
        if icc:
            if hasattr(icc, 'data'):
                hsh = hashlib.sha1(icc.data).hexdigest()
        if hsh:
            return self.filter(
                icc__isnull=False,
                icchash__exact=hsh,
            )
        return self.none()
    
    @delegate
    def discordant_profile(self, icc=None, hsh=None):
        if icc:
            if hasattr(icc, 'data'):
                hsh = hashlib.sha1(icc.data).hexdigest()
        if hsh:
            return self.filter(
                Q(icc__isnull=False) & \
                ~Q(icchash__exact=hsh)
            )
        return self.none()
    
    @delegate
    def rndicc(self):
        return self.with_profile().rnd()

class ImageWithMetadataManager(DelegateManager):
    __queryset__ = ImageWithMetadataQuerySet

class ImageWithMetadata(ImageModel):
    class Meta:
        abstract = True
        verbose_name = "Image Metadata"
        verbose_name = "Image Metadata Objects"
    
    objects = ImageWithMetadataManager()
    
    # We can sort by these color values.
    dominantcolor = RGBColorField(verbose_name="Dominant Color",
        extractor=lambda instance: instance.dominanthex())
    
    meancolor = RGBColorField(verbose_name="Mean Color",
        extractor=lambda instance: instance.meanhex())
    
    averagecolor = RGBColorField(verbose_name="Average Color",
        extractor=lambda instance: instance.averagehex())
    
    mediancolor = RGBColorField(verbose_name="Median Color",
        extractor=lambda instance: instance.medianhex())
    
    # EXIF image metadata
    exif = EXIFMetaField(verbose_name="EXIF data",
        storage=_storage,
        editable=True,
        blank=True,
        null=True)
    
    # ICC color management profile data
    icc = ICCMetaField(verbose_name="ICC data",
        hash_field='icchash',
        editable=False,
        null=True)
    
    # Unique hash of ICC profile data (for fast DB searching)
    icchash = ICCHashField(verbose_name="ICC embedded profile hash",
        unique=False, # ICCHashField defaults to unique=True
        editable=True,
        blank=True,
        null=True)
    
    # Unique hash of the image data
    imagehash = ImageHashField(verbose_name="Image data hash",
        editable=True)
    
    def proofimage(self, proofprofile, sourceprofile=None, **kwargs):
        
        if sourceprofile is None:
            if self.iccmodel:
                sourceprofile = self.iccmodel
        
        proof = Proof(
            content_type=self.content_type,
            object_id=self.pk,
            #sourceimage=self,
            sourceprofile=sourceprofile,
            proofprofile=proofprofile,
        )
        
        if 'intent' in kwargs:
            proof.intent = kwargs.pop('intent')
        
        if 'proofintent' in kwargs:
            proof.proofintent = kwargs.pop('proofintent')
        
        return proof
    
    @property
    def content_type(self):
        return ContentType.objects.get_for_model(self.__class__)
    
    @property
    def iccmodel(self):
        try:
            return ICCModel.objects.get(icchash=self.icchash)
        except ICCModel.DoesNotExist:
            return None
    
    @property
    def same_profile_set(self):
        return self.__class__.objects.matching_profile(hsh=self.icchash)
    
    @property
    def different_profile_set(self):
        return self.__class__.objects.discordant_profile(hsh=self.icchash)
    
    @property
    def icctransformer(self):
        return self.icc.transformer
    
    def __repr__(self):
        return "<%s #%s>" % (self.__class__.__name__, self.pk)


class ICCQuerySet(models.query.QuerySet):
    
    def __init__(self, *args, **kwargs):
        super(ICCQuerySet, self).__init__(*args, **kwargs)
        random.seed()
    
    @delegate
    def rnd(self):
        return random.choice(self.all())
    
    @delegate
    def profile_match(self, icc=None, hsh=None):
        if icc:
            if hasattr(icc, 'data'):
                hsh = hashlib.sha1(icc.data).hexdigest()
        if hsh:
            return self.get(
                icc__isnull=False,
                icchash__exact=hsh,
            )
        return None
    
    @delegate
    def profile_search(self, search_string='', sqs=False):
        """
        Arbitrarily searches the Haystack index of profile metadata, if it's available.
        """
        if HAYSTACK and search_string:
            if not hasattr(self, 'srcher'):
                self.srcher = SearchQuerySet().models(self.model)
            
            results = self.srcher.auto_query(search_string)
            
            if sqs:
                # return the SearchQuerySet if we were asked for it explicitly
                return results
            else:
                # default to constructing a QuerySet from the IDs we got
                return self.filter(pk__in=(result.object.pk for result in results))
        
        if not HAYSTACK:
            logg.warning("ICCQuerySet.profile_search() Haystack Search isn't configured -- not filtering profiles (q='%s')." % search_string)
        
        return self.all()

class ICCManager(DelegateManager):
    __queryset__ = ICCQuerySet

class ICCModel(models.Model):
    class Meta:
        abstract = False
        verbose_name = "ICC Profile"
        verbose_name_plural = "ICC Profile Objects"
    
    def __init__(self, *args, **kwargs):
        super(ICCModel, self).__init__(*args, **kwargs)
        self._storage = _storage
    
    objects = ICCManager()
    
    iccfile = ICCField(verbose_name="ICC binary file",
        storage=_storage,
        blank=True,
        null=True,
        upload_to="icc/uploads",
        data_field='icc', # points to ICCDataField
        hash_field='icchash', # points to ICCHashField
        max_length=255)
    
    icc = ICCDataField(verbose_name="ICC data",
        editable=False,
        blank=True,
        null=True)
    
    icchash = ICCHashField(verbose_name="ICC file hash")
    
    createdate = models.DateTimeField('Created on',
        default=datetime.now,
        blank=True,
        editable=False)
    
    modifydate = models.DateTimeField('Last modified on',
        default=datetime.now,
        blank=True,
        editable=False)
    
    @property
    def icctransformer(self):
        return self.icc.transformer
    
    @property
    def lcmsinstance(self):
        return ImageCms.ImageCmsProfile(self.iccfile.file)
    
    def get_profiled_images(self, modl):
        """
        Retrieve ImageModel/ImageWithMetadata subclasses that have
        embedded profile data that matches this ICCModel instances'
        profile. Matches are detected by comparing ICCHashFields.
        
        """
        # use model's with_matching_profile shortcut call, if present
        if hasattr(modl.objects, 'matching_profile'):
            return modl.objects.matching_profile(hsh=self.icchash)
        
        # no with_matching_profile shortcut; scan fields for an ICCProfileHash
        modlfield = None
        if modl._meta:
            for field in modl._meta.fields:
                if isinstance(field, ICCHashField):
                    modlfield = getattr(field, 'name', None)
                    break
        
        if modlfield:
            lookup = str('%s__exact' % modlfield)
            if hasattr(modl.objects, 'with_profile'):
                # limit query to model instances with profiles, if possible
                return modl.objects.with_profile().filter(**{ lookup: self.icchash })
            modl.objects.filter(**{ lookup: self.icchash })
        
        else:
            logg.info("ICCModel.get_profiled_images() failed for model %s -- no ICCHashField defined and no profile hash lookup methods found" % modl.__class__.__name__)
        
        return modl.objects.none()
    
    def save(self, force_insert=False, force_update=False, **kwargs):
        self.modifydate = datetime.now()
        super(ICCModel, self).save(force_insert, force_update, **kwargs)
    
    def __unicode__(self):
        
        if self.icc:
            return u'%s' % (
                self.icc.getDescription(),
            )
        
        return u'-empty-'


"""
South has assuaged me, so I'm happy to assuage it.

"""
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    # 'models inspector' sounds like the punchline of a junior-high-era joke
    add_introspection_rules(
        rules = [
            ((ICCField,), [], {
            }),
        ], patterns = [
            '^imagekit\.modelfields\.ICCField',
        ]
    )

