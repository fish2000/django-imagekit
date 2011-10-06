import base64, hashlib, numpy, uuid
from django.conf import settings
from django.db import models
from django.db.models import fields
from django.db.models.fields import files
from django.db.models import signals
from django.utils.translation import ugettext_lazy
from django.core.files import File
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import ObjectDoesNotExist
#from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from ICCProfile import ICCProfile
from imagekit import colors
from imagekit.utils import logg
from imagekit.utils import EXIF
from imagekit.utils.json import json
from imagekit import signals as iksignals
from imagekit.widgets import RGBColorFieldWidget
import imagekit
import imagekit.models



def get_modified_time(instance):
    if instance is not None:
        storage = getattr(instance, '_storage', None)
        instancename = getattr(instance._imgfield, 'name', None)
        if storage and instancename:
            try:
                return storage.modified_time(instancename)
            except AttributeError:
                pass
    return None


class ICCDataField(models.TextField):
    """
    Model field representing an ICC profile instance.
    
    Represented in python as an ICCProfile instance -- see ICCProfile.py for details.
    The profile itself is stored in the database as unicode data. I haven't had any
    problems cramming fairly large profiles (>2 megs) into postgres; let me know if
    your backend chokes on profiles you throw its way.
    
    Example usage:
    -------------------------
    
    from django.db import models
    import imagekit.models
    import imagekit.modelfields
    from imagekit.ICCProfile import ICCProfile
    
    class ImageWithProfile(imagekit.models.ImageModel):
        class IKOptions:
            spec_module = ...
            image_field = 'image'
        image = models.ImageField( ... )
        iccdata = imagekit.modelfields.ICCDataField(editable=False, null=True)
        
        def save(self, force_insert=False, force_update=False):
            if self.pilimage:
                if self.pilimage.info.get('icc_profile'):
                    self.iccdata = ICCProfile(self.pilimage.info['icc_profile'])
            super(ImageWithProfile, self).save(force_insert, force_update)
    
    -------------------------
    
    >>> from myapp.models import ImageWithProfile
    >>> axim = ImageWithProfile.objects.all()[0]
    >>> axim.iccdata.calculateID()
    "\xd95\xa4/\x04\xcf'\xa2\xd9\xf2\x17\x97\xd5\x0c\xf2j"
    >>> axim.iccdata.getIDString
    '2TWkLwTPJ6LZ8heX1Qzyag=='
    >>> axim.iccdata.getCopyright()
    u'Copyright (c) 1998 Hewlett-Packard Company'
    >>> axim.iccdata.getDescription()
    u'sRGB IEC61966-2.1'
    >>> axim.iccdata.getViewingConditionsDescription()
    u'Reference Viewing Condition in IEC61966-2.1'
    
    -------------------------
    
    """
    __metaclass__ = models.SubfieldBase
    
    def to_python(self, value):
        """
        Always return a valid ICCProfile instance, or None.
        """
        if value:
            if isinstance(value, ICCProfile):
                return value
            return ICCProfile(base64.b64decode(value))
        return None
    
    def get_prep_value(self, value):
        """
        Always return the profile data as a string, or an empty string.
        """
        if value:
            if isinstance(value, ICCProfile):
                return value.data
            if len(value) > 0:
                return value
        return value
    
    def get_db_prep_value(self, value, connection=None, prepared=False):
        """
        Always return a valid unicode data string.
        """
        if not prepared:
            value = self.get_prep_value(value)
        if value:
            return base64.b64encode(value)
        return value
    
    def value_to_string(self, obj):
        """
        Return unicode data (for now) suitable for serialization (JSON, pickle, etc)
        """
        return self.get_db_prep_value(self._get_val_from_obj(obj))
    
    def south_field_triple(self):
        """
        Represent the field properly to the django-south model inspector.
        See also: http://south.aeracode.org/docs/extendingintrospection.html
        """
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.ICCDataField', args, kwargs)


class ICCMetaField(ICCDataField):
    """
    This ICCDataField subclass will automatically refresh itself
    with ICC data it finds in the image classes' PIL instance. The
    methods it impelemnts are designed to work with the ImageWithMetadata
    abstract base class to accomplish this feat, using signals.
    
    """
    def __init__(self, *args, **kwargs):
        self.pil_reference = kwargs.pop('pil_reference', 'pilimage')
        self.hash_field = kwargs.pop('hash_field', None)
        super(ICCMetaField, self).__init__(**kwargs)
    
    def contribute_to_class(self, cls, name):
        super(ICCMetaField, self).contribute_to_class(cls, name)
        signals.pre_save.connect(self.check_icc_field, sender=cls)
        iksignals.refresh_icc_data.connect(self.refresh_icc_data, sender=cls)
    
    def check_icc_field(self, **kwargs): # signal, sender, instance
        if not kwargs.get('raw', False):
            instance = kwargs.get('instance')
            if not getattr(instance, self.name, None):
                iksignals.refresh_icc_data.send(sender=instance.__class__, instance=instance)
    
    def refresh_icc_data(self, **kwargs): # signal, sender, instance
        """
        Stores ICC profile data in the field before saving, and refreshes
        the profile hash if an ICCHashField has been specified.
        
        """
        instance = kwargs.get('instance')
        
        try:
            pil_reference = self.pil_reference
            
            if callable(pil_reference):
                pilimage = pil_reference(instance)
            else:
                pilimage = getattr(instance, getattr(self, 'pil_reference', 'pilimage'))
        
        except AttributeError, err:
            logg.warning("*** Couldn't refresh ICC data with custom callable (AttributeError was thrown: %s)" % err)
            return
        except TypeError, err:
            logg.warning("*** Couldn't refresh ICC data with custom callable (TypeError was thrown: %s)" % err)
            return
        except IOError, err:
            logg.warning("*** Couldn't refresh ICC data with custom callable (IOError was thrown: %s)" % err)
            return
        
        profile_string = ''
        
        if pilimage:
            try:
                profile_string = pilimage.info.get('icc_profile', '')
            except ObjectDoesNotExist:
                logg.info("Exception was raised when trying to get the icc profile string")
            
            if len(profile_string):
                #logg.info("Saving icc profile for %s %s ..." % (instance.__class__.__name__, instance.id))
                iccdata = ICCProfile(profile_string)
                setattr(instance, self.name, ICCProfile(profile_string))
                logg.info("Saved icc profile '%s' for %s" % (instance.icc.getDescription(), instance.id))
                
                # refresh profile hash
                if self.hash_field:
                    hsh = hashlib.sha1(iccdata.data).hexdigest()
                    setattr(instance, self.hash_field, hsh)
                    logg.info("Saved icc profile hash '%s' in ICCHashField %s" % (hsh, self.hash_field))
                
                # save if sent asynchronously
                dequeue_runmode = kwargs.get('dequeue_runmode', None)
                enqueue_runmode = kwargs.get('enqueue_runmode', None)
                if dequeue_runmode is not None:
                    if not dequeue_runmode == enqueue_runmode:
                        if dequeue_runmode == imagekit.IK_ASYNC_DAEMON:
                            instance.save_base()
                
    
    def south_field_triple(self):
        """
        Represent the field properly to the django-south model inspector.
        See also: http://south.aeracode.org/docs/extendingintrospection.html
        """
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.ICCMetaField', args, kwargs)


class EXIFMetaField(models.TextField):
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        self._storage = kwargs.pop('storage', None)
        if not self._storage:
            try:
                self._storage = getattr(settings, 'IK_STORAGE', None)()
            except:
                self._storage = FileSystemStorage()
            else:
                if not self._storage:
                    self._storage = FileSystemStorage()
        
        super(EXIFMetaField, self).__init__(*args, **kwargs)
    
    def to_python(self, value):
        from imagekit.utils.json import json
        if not value:
            return None
        if isinstance(value, basestring):
            try:
                return json.loads(str(value))
            except ValueError:
                pass
        return value
    
    def get_db_prep_save(self, value, **kwargs):
        if not value or value == "":
            return None
        value = json.dumps(value)
        return super(EXIFMetaField, self).get_db_prep_save(value, **kwargs)
    
    def contribute_to_class(self, cls, name):
        super(EXIFMetaField, self).contribute_to_class(cls, name)
        signals.post_save.connect(self.check_exif_field, sender=cls)
        iksignals.refresh_exif_data.connect(self.refresh_exif_data, sender=cls)
    
    def check_exif_field(self, **kwargs): # signal, sender, instance
        if not kwargs.get('raw', False):
            instance = kwargs.get('instance')
            
            # use the PIL accessor to test whether or not we have any EXIF data
            p = instance.pilimage
            if hasattr(p, "_getexif"):
                if not getattr(instance, self.name, None):
                    iksignals.refresh_exif_data.send(sender=instance.__class__, instance=instance)

    def refresh_exif_data(self, **kwargs): # signal, sender, instance
        """
        Stores EXIF profile data in the field before saving.
        Unlike ICC data represented by an ICCProfile instance, the EXIF data
        we get back from EXIF.py is a plain dict [don't we all wish. -ed].
        As a result, this field's refresh method is much simpler than its
        counterpart in ICCMetaField, as we only have to go one-way, as it were.
        
        """
        instance = kwargs.get('instance')
        
        # get the EXIF data out of the image
        try:
            im = instance.image
            im.seek(0)
            exif_dict = EXIF.process_file(im)
        except:
            try:
                im = instance.image
                im.seek(0)
                exif_dict = EXIF.process_file(im, details=False)
            except:
                exif_dict = {}
        
        # delete any JPEGThumbnail data we might have found
        if 'JPEGThumbnail' in exif_dict.keys():
            del exif_dict['JPEGThumbnail']
        
        exif_out = {}
        for k, v in exif_dict.items():
            exif_out.update({ k: getattr(v, 'printable') or v, })
        
        # store it appropruately
        if len(exif_out.keys()) > 0:
            setattr(instance, self.name, exif_out)
            logg.info("Saved exif data for %s: (%s tags)" % (
                instance.id,
                #"', '".join(exif_out.keys()),
                len(exif_out.keys()),
            ))
            
            # save if sent asynchronously
            dequeue_runmode = kwargs.get('dequeue_runmode', None)
            enqueue_runmode = kwargs.get('enqueue_runmode', None)
            if dequeue_runmode is not None:
                if not dequeue_runmode == enqueue_runmode:
                    if dequeue_runmode == imagekit.IK_ASYNC_DAEMON:
                        instance.save_base()
    
    def south_field_triple(self):
        """
        Represent the field properly to the django-south model inspector.
        See also: http://south.aeracode.org/docs/extendingintrospection.html
        """
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.EXIFMetaField', args, kwargs)


class ImageHashField(fields.CharField):
    """
    Store a unique hash of the data in the image field of an ImageModel.
    
    Custom callables can be specified for the 'pil_reference' and 'hasher' kwargs:
    
        * 'pil_reference' works as it does in ICCMetaField and friends (see the above) --
           it can be a string that names a field name on the ImageModel instance in question,
           or a callable. The pil image it yields provides the data for the hasher.
    
        * 'hasher' can also be either a string or a callable. If it's a string, we assume
           that you're naming a hash algorithm from the hashlib module. If it's a callable,
           it should take the value of tostring() from a pil Image instance as its one
           argument, and return a string that uniquely and deterministically identifies
           the stringified image data it was given.
    
    NOTE: ImageHashField is a subclass of django.db.models.CharField, which requires 
    max_length to be specified. We default to 40, which is the value of:
    
        len(hashlib.sha1(pil_reference.tostring()).hexdigest())
    
    ... So if you are using another algorithm, make sure to specify max_length in your
    ImageHashField declarations. Ideally, your hashes will always be the same length,
    and your max_length should be whatever that number is; otherwise make sure you set it
    to something that accommodates your hash length (and not more).
    
    """
    
    def __init__(self, *args, **kwargs):
        self.pil_reference = kwargs.pop('pil_reference', 'pilimage')
        self.hasher = kwargs.pop('hasher', 'sha1')
        
        kwargs.setdefault('db_index', True)
        kwargs.setdefault('max_length', 40) # size of sha1, the deafult
        kwargs.setdefault('editable', False)
        kwargs.setdefault('unique', False)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(ImageHashField, self).__init__(*args, **kwargs)
    
    def contribute_to_class(self, cls, name):
        super(ImageHashField, self).contribute_to_class(cls, name)
        signals.pre_save.connect(self.check_hash_field, sender=cls)
        iksignals.refresh_hash.connect(self.refresh_hash, sender=cls)
    
    def check_hash_field(self, **kwargs): # signal, sender, instance
        if not kwargs.get('raw', False):
            instance = kwargs.get('instance')
            if not getattr(instance, self.name, None):
                iksignals.refresh_hash.send(sender=instance.__class__, instance=instance)
    
    def refresh_hash(self, **kwargs): # signal, sender, instance
        """
        Stores image hash data in the field before saving.
        
        """
        instance = kwargs.get('instance')
        
        try:
            pil_reference = self.pil_reference
            
            if callable(pil_reference):
                pilimage = pil_reference(instance)
            else:
                pilimage = getattr(instance, getattr(self, 'pil_reference', 'pilimage'))
        
        except AttributeError, err:
            logg.warning("*** Couldn't get pilimage reference to refresh image hash (AttributeError was thrown: %s)" % err)
            return
        except TypeError, err:
            logg.warning("*** Couldn't get pilimage reference to refresh image hash (TypeError was thrown: %s)" % err)
            return
        except IOError, err:
            logg.warning("*** Couldn't get pilimage reference to refresh image hash (IOError was thrown: %s)" % err)
            return
        
        if pilimage:
            try:
                hash_string = ''
                hashee = pilimage.tostring()
                hasher = self.hasher
                
                if callable(hasher):
                    # use the custom callable
                    hash_string = hasher(pil_reference)
                    setattr(instance, self.name, hash_string)
                else:
                    # use the specified alorithm in hashlib to create a digest
                    hash_string = getattr(hashlib, hasher)(hashee).hexdigest()
                    setattr(instance, self.name, hash_string)
            
            except AttributeError, err:
                logg.warning("*** Couldn't refresh image hash (AttributeError was thrown: %s)" % err)
                return
            except TypeError, err:
                logg.warning("*** Couldn't refresh image hash (TypeError was thrown: %s)" % err)
                return
            except IOError, err:
                logg.warning("*** Couldn't refresh image hash (IOError was thrown: %s)" % err)
                return
            
            # save if sent asynchronously
            dequeue_runmode = kwargs.get('dequeue_runmode', None)
            enqueue_runmode = kwargs.get('enqueue_runmode', None)
            if dequeue_runmode is not None:
                if not dequeue_runmode == enqueue_runmode:
                    if dequeue_runmode == imagekit.IK_ASYNC_DAEMON:
                        instance.save_base()
    
    def south_field_triple(self):
        """
        Represent the field properly to the django-south model inspector.
        See also: http://south.aeracode.org/docs/extendingintrospection.html
        """
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.ImageHashField', args, kwargs)


class ICCHashField(fields.CharField):
    """
    Store the sha1 of the ICC profile file we're talking about.
    
    ICCHashField is used to uniquely identify ICCModel instances, which are stored
    as database-tracked files, a la django's ImageField -- you can't just use
    unique=True because when we mean 'unique', we mean the binary contents of the
    file and not the path, which is a problem ICCDataField doesn't have; calculating
    the hash dynamically might sound fine until you have an archive of 10,000 ICC files
    on s3, in which case you will want to avoid opening up and hashing everything
    whenever you hit save in the admin (or what have you).
    
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('db_index', True)
        kwargs.setdefault('max_length', 40)
        kwargs.setdefault('editable', False)
        #kwargs.setdefault('unique', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(ICCHashField, self).__init__(*args, **kwargs)
    
    def south_field_triple(self):
        """
        Represent the field properly to the django-south model inspector.
        See also: http://south.aeracode.org/docs/extendingintrospection.html
        """
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.ICCHashField', args, kwargs)


class RGBColorField(models.CharField):
    """"
    Field for storing one 24-bit companded RGB color triple, encoded as a hex string.
    
    (As in what is often what is meant by just 'a color'. Typically like so: '#FF192C'.)
    
    Works most harmoniously with imagekit.widgets.RGBColorFieldWidget as the UI, and the
    patched version NodeBox colors.Color we're bundling as the datastructure -- one of
    the patches sets up colors.Color.__repr__() for seamless serialization. 
    
    The current NodeBox color module's members are bristling with quick and simple,
    yet lossy and slightly non-deterministic, color-conversion methods for many
    spaces/modes/types/datastructures. For 99 percent of people, lossy color
    conversions between companded 8-bit values are fine and dandy. But you,
    my friend... you didn't download the fish2000 ultra-colorphilic ImageKit
    fork for colorphiles because you're one of the typical 99 percent. Amirite?
    Rest assured, I'll refactor it soon; in the meantime, knowing is 1/2 the battle.
    
    """
    __metaclass__ = models.SubfieldBase
    
    def __init__(self, *args, **kwargs):
        self.extractor = kwargs.pop('extractor', None)
        
        kwargs.setdefault('db_index', True)
        kwargs.setdefault('max_length', 8)
        kwargs.setdefault('editable', True)
        kwargs.setdefault('unique', False)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super(RGBColorField, self).__init__(*args, **kwargs)
    
    def to_python(self, value):
        if hasattr(value, 'hex'):
            return value
        if value is not None:
            return colors.Color("#%s" % value)
        return None
    
    def get_db_prep_value(self, value, connection=None, prepared=None):
        if hasattr(value, 'hex'):
            return getattr(value, 'hex').upper()
        return value
    
    def value_to_string(self, obj):
        return self.get_db_prep_value(self._get_val_from_obj(obj))
    
    def formfield(self, **kwargs):
        kwargs['widget'] = RGBColorFieldWidget(attrs={
            'class': "colorfield",
            'size': 7,
        })
        return super(RGBColorField, self).formfield(**kwargs)
    
    def contribute_to_class(self, cls, name):
        super(RGBColorField, self).contribute_to_class(cls, name)
        signals.pre_save.connect(self.check_rgb_color_field, sender=cls)
        iksignals.refresh_color.connect(self.refresh_color, sender=cls)
    
    def check_rgb_color_field(self, **kwargs):
        if not kwargs.get('raw', False):
            instance = kwargs.get('instance')
            if not getattr(instance, self.name, None):
                if self.extractor is not None:
                    iksignals.refresh_color.send(sender=instance.__class__, instance=instance)
    
    def refresh_color(self, **kwargs): # signal, sender, instance
        """
        Stores image hash data in the field before saving.
        
        """
        instance = kwargs.get('instance')
        extractor = self.extractor
        
        if callable(extractor):
            try:
                setattr(instance, self.name, extractor(instance))
            
            except AttributeError, err:
                logg.warning("""*** Couldn't refresh color '%s' (AttributeError was thrown: %s)""" % (self.name, err))
                return
            except TypeError, err:
                logg.warning("""*** Couldn't refresh color '%s' (TypeError was thrown: %s)""" % (self.name, err))
                return
            except IOError, err:
                logg.warning("""*** Couldn't refresh color '%s' (IOError was thrown: %s)""" % (self.name, err))
                return
        else:
            # call the named method on the ImageModel instance
            try:
                color_hex_value = getattr(instance, getattr(self, 'extractor', instance.dominanthex))()
                setattr(instance, self.name, color_hex_value)
            
            except AttributeError, err:
                logg.warning("""*** Couldn't refresh color '%s' (AttributeError was thrown: %s)""" % (self.name, err))
                return
            except TypeError, err:
                logg.warning("""*** Couldn't refresh color '%s' (TypeError was thrown: %s)""" % (self.name, err))
                return
            except IOError, err:
                logg.warning("""*** Couldn't refresh color '%s' (IOError was thrown: %s)""" % (self.name, err))
                return
        
        # save if sent asynchronously
        dequeue_runmode = kwargs.get('dequeue_runmode', None)
        enqueue_runmode = kwargs.get('enqueue_runmode', None)
        if dequeue_runmode is not None:
            if not dequeue_runmode == enqueue_runmode:
                if dequeue_runmode == imagekit.IK_ASYNC_DAEMON:
                    instance.save_base()
    
    def south_field_triple(self):
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.RGBColorField', args, kwargs)


"""
FileField subclasses for ICC profile documents.

Each of the following fields and helpers are subclassed from django's FileField components;
I derived all of them from reading the code morsels that implement django ImageFileFields;
they're well-commented, so if any of this confuses you, read that stuff -- it's in and around
django.db.models.fields.images I believe.

"""
class ICCFile(File):
    """
    django.core.files.File subclass with ICC profile support.
    """
    def _load_icc_file(self):
        if not hasattr(self, "_profile_cache"):
            close = self.closed
            self.open()
            pos = self.tell()
            dat = self.read()
            hsh = hashlib.sha1(dat).hexdigest()
            
            self._profile_cache = (ICCProfile(profile=dat), hsh)
            
            if close:
                self.close()
            else:
                self.seek(pos)
        return self._profile_cache
    
    def _get_iccdata(self):
        return self._load_icc_file()[0]
    iccdata = property(_get_iccdata)
    
    def _get_hsh(self):
        return self._load_icc_file()[1]
    hsh = property(_get_hsh)

class ICCFileDescriptor(files.FileDescriptor):
    """
    django.db.models.fields.files.FileDescriptor subclass with ICC profile support.
    """
    def __set__(self, instance, value):
        previous_file = instance.__dict__.get(self.field.name)
        super(ICCFileDescriptor, self).__set__(instance, value)
        if previous_file is not None:
            self.field.update_data_fields(instance, force=True)

class ICCFieldFile(ICCFile, files.FieldFile):
    """
    django.db.models.fields.files.FileDescriptor subclass with ICC profile support.
    """
    def delete(self, save=True):
        if hasattr(self, '_profile_cache'):
            del self._profile_cache
        super(ICCFieldFile, self).delete(save)

class ICCField(files.FileField):
    """
    django.db.models.fields.files.FileField subclass with ICC profile support.
    """
    attr_class = ICCFieldFile
    descriptor_class = ICCFileDescriptor
    description = ugettext_lazy("ICC file path")
    
    def __init__(self, verbose_name=None, name=None, data_field=None, hash_field=None, **kwargs):
        self.data_field = data_field
        self.hash_field = hash_field
        self.__class__.__base__.__init__(self, verbose_name, name, **kwargs)
    
    def contribute_to_class(self, cls, name):
        super(ICCField, self).contribute_to_class(cls, name)
        signals.post_init.connect(self.update_data_fields, sender=cls, dispatch_uid=uuid.uuid4().hex)
    
    def update_data_fields(self, instance, force=False, *args, **kwargs):
        has_data_fields = self.data_field or self.hash_field
        if not has_data_fields:
            return
        
        ffile = getattr(instance, self.attname)
        if not ffile and not force:
            return
        
        data_fields_filled = not(
            (self.data_field and not getattr(instance, self.data_field))
            or (self.hash_field and not getattr(instance, self.hash_field))
        )
        if data_fields_filled and not force:
            return
        
        try:
            if ffile:
                if ffile.iccdata:
                    iccdata = ffile.iccdata
                else:
                    iccdata = None
                if ffile.hsh:
                    hsh = ffile.hsh
                else:
                    hsh = None
            else:
                iccdata = None
                hsh = None
        except ValueError:
            iccdata = None
            hsh = None
        
        if self.data_field:
            setattr(instance, self.data_field, iccdata)
        if self.hash_field:
            setattr(instance, self.hash_field, hsh)
    
    def south_field_triple(self):
        """
        Represent the field properly to the django-south model inspector.
        See also: http://south.aeracode.org/docs/extendingintrospection.html
        """
        from south.modelsinspector import introspector
        args, kwargs = introspector(self)
        return ('imagekit.modelfields.ICCField', args, kwargs)
