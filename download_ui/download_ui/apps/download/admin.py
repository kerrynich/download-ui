from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import UserRegisterForm
from .models import Download, Extension, Format, Quality, Source, Command, UserProfile

# Register your models here.


class CustomUserAdmin(UserAdmin):
    model = UserProfile
    add_form = UserRegisterForm
    fieldsets = (
        *UserAdmin.fieldsets,
        (
            'Custom Flags',
            {
                'fields': (
                    'is_approved',
                )
            }
        )
    )


admin.site.register(Download)
admin.site.register(Extension)
admin.site.register(Quality)
admin.site.register(Format)
admin.site.register(Source)
admin.site.register(Command)
admin.site.register(UserProfile, CustomUserAdmin)
