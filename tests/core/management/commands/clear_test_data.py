import shutil
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    help = ('Clears testing data.')
    requires_model_validation = False
    can_import_settings = True

    def handle_noargs(self, **options):
        from django.conf import settings
        shutil.rmtree(settings.tempdata)
