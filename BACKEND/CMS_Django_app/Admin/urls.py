from rest_framework.routers import DefaultRouter
from .views import (
    StaffViewSet,
    SpecializationViewSet,
    DoctorProfileViewSet,
    DoctorScheduleViewSet
)

# =========================================================
# ROUTER CONFIGURATION
# =========================================================

router = DefaultRouter()

# STAFF MANAGEMENT
router.register(r'staff', StaffViewSet, basename='staff')

# SPECIALIZATION MANAGEMENT
router.register(r'specializations', SpecializationViewSet, basename='specialization')

# DOCTOR PROFILE MANAGEMENT
router.register(r'doctors', DoctorProfileViewSet, basename='doctor')

# DOCTOR SCHEDULE MANAGEMENT
router.register(r'schedules', DoctorScheduleViewSet, basename='schedule')


# =========================================================
# URL PATTERNS
# =========================================================

urlpatterns = router.urls