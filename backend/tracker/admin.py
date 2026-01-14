from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import HealthProfile, DailyMetric, HealthJournal, CoachLink

User = get_user_model()

# nếu đã lỡ register ở nơi khác thì unregister trước
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("id", "username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Role", {"fields": ("role",)}),
    )


# (tuỳ bạn) register thêm để dễ nhìn DB
admin.site.register(HealthProfile)
admin.site.register(DailyMetric)
admin.site.register(HealthJournal)
admin.site.register(CoachLink)
