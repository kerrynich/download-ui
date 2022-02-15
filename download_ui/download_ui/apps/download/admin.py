from django.contrib import admin

from .models import Download, Extension, Format, Quality

# Register your models here.

admin.site.register(Download)
admin.site.register(Extension)
admin.site.register(Quality)
admin.site.register(Format)