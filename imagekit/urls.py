from django.conf import settings
from django.conf.urls.defaults import patterns, url, include

# imagekit URLs
app_patterns = patterns('',

    url(r'^image/(?P<app_label>[\w\_]+)/(?P<modlcls>[\w]+)/(?P<pk>[\w\-]+)/?$',
        'imagekit.views.image', name="image"),
    
    url(r'^image-property/(?P<app_label>[\w\_]+)/(?P<modlcls>[\w]+)/(?P<pk>[\w\-]+)/(?P<prop_name>[\w\-\_]+)/?$',
        'imagekit.views.image_property', name="image_property"),

)

# imagekit URL namespace
urlpatterns = patterns('',

    url(r'^view/', include(app_patterns,
        namespace='imagekit', app_name='imagekit')),

)

