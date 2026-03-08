from django.contrib import admin

# Register your models here.


from django.contrib import admin
from .models import Staff, Specialization, DoctorProfile, DoctorSchedule


admin.site.register(Staff)
admin.site.register(Specialization)
admin.site.register(DoctorProfile)
admin.site.register(DoctorSchedule)
