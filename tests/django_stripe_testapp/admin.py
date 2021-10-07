from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


User = get_user_model()


class CustomUserAdmin(UserAdmin):

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'last_login', 'allowed_access_until',
                    'stripe_customer_id', 'is_active',)
    ordering = ('email',)
    search_fields = ('first_name', 'last_name', 'email', 'stripe_customer_id')
    list_per_page = 20
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    fieldsets = (
        (None, {'fields': ('email',)}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Payments'), {'fields': ('stripe_customer_id', 'allowed_access_until')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_related('groups')
        return qs


admin.site.register(User, CustomUserAdmin)
