
from django.http import HttpResponse, HttpResponseNotFound
from django.db.models.loading import cache
from django.views.decorators.cache import never_cache

@never_cache
def image(request, app_label, modlcls, pk):
    modl = cache.get_model(app_label, modlcls)
    
    if modl is None:
        return HttpResponseNotFound()
    
    try:
        instance = modl.objects.get(pk=pk)
    except modl.DoesNotExist:
        return HttpResponseNotFound()
    
    out = HttpResponse(mimetype="image/png")
    instance.pilimage.save(out, "PNG")
    return out


def image_property(request, app_label, modlcls, pk, prop_name):
    modl = cache.get_model(app_label, modlcls)
    
    if modl is None:
        return HttpResponseNotFound()
    
    try:
        instance = modl.objects.get(pk=pk)
    except modl.DoesNotExist:
        return HttpResponseNotFound()
    
    if hasattr(instance, prop_name):
        out = HttpResponse(mimetype="image/png")
        getattr(instance, prop_name).image.save(out, "PNG")
        return out
    
    return HttpResponseNotFound()

    