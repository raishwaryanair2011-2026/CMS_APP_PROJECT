from rest_framework.routers import DefaultRouter
from .views import (
    StaffViewSet,
    SpecializationViewSet,
    DoctorProfileViewSet,
    DoctorScheduleViewSet
)

router = DefaultRouter()

router.register(r'staff', StaffViewSet)
router.register(r'specializations', SpecializationViewSet)
router.register(r'doctors', DoctorProfileViewSet)
router.register(r'schedules', DoctorScheduleViewSet)

urlpatterns = router.urls