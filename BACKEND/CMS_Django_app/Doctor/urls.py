from django.urls import path, include
from rest_framework_nested import routers

from .views import (
    ConsultationViewSet,
    PrescriptionViewSet,
    MedicinePrescriptionViewSet,
    LabTestPrescriptionViewSet,
)


# ======================================================
# ROOT ROUTER
# ======================================================

# FIX: Replace the flat DefaultRouter with a nested router structure using
# drf-nested-routers (pip install drf-nested-routers).
#
# Previously all four resources were registered at the top level:
#   /consultations/
#   /prescriptions/
#   /medicine-prescriptions/
#   /lab-test-prescriptions/
#
# This allowed clients to access medicines and lab tests without any
# consultation context, and made it possible to create a medicine
# prescription without knowing which consultation it belongs to.
#
# The new hierarchy enforces the natural ownership chain:
#
#   /consultations/                                         <- ConsultationViewSet
#   /consultations/{consultation_pk}/prescription/          <- PrescriptionViewSet
#   /consultations/{consultation_pk}/prescription/medicines/
#                                                           <- MedicinePrescriptionViewSet
#   /consultations/{consultation_pk}/prescription/lab-tests/
#                                                           <- LabTestPrescriptionViewSet

router = routers.DefaultRouter()
router.register(
    r"consultations",
    ConsultationViewSet,
    basename="consultation",
)

# ======================================================
# NESTED ROUTER — PRESCRIPTION UNDER CONSULTATION
# ======================================================

# A consultation has exactly one prescription (OneToOne), so the nested
# URL uses the singular form 'prescription' rather than 'prescriptions'.
# drf-nested-routers still generates the standard list/detail actions.
consultation_router = routers.NestedDefaultRouter(
    router,
    r"consultations",
    lookup="consultation",
)
consultation_router.register(
    r"prescription",
    PrescriptionViewSet,
    basename="consultation-prescription",
)

# ======================================================
# NESTED ROUTER — MEDICINES & LAB TESTS UNDER PRESCRIPTION
# ======================================================

prescription_router = routers.NestedDefaultRouter(
    consultation_router,
    r"prescription",
    lookup="prescription",
)
prescription_router.register(
    r"medicines",
    MedicinePrescriptionViewSet,
    basename="prescription-medicines",
)
prescription_router.register(
    r"lab-tests",
    LabTestPrescriptionViewSet,
    basename="prescription-lab-tests",
)

# ======================================================
# URL PATTERNS
# ======================================================

# FIX: Add API versioning prefix (v1) so the React frontend is never
# locked into unversioned URLs. When breaking changes are needed, a v2
# prefix can be introduced without affecting existing clients.
#
# These patterns are included in the project's main urls.py like so:
#
#   path("api/v1/doctor/", include("Doctor.urls")),
#
# Which produces the full URL structure:
#
#   GET  /api/v1/doctor/consultations/
#   POST /api/v1/doctor/consultations/
#   GET  /api/v1/doctor/consultations/{consultation_pk}/
#   GET  /api/v1/doctor/consultations/{consultation_pk}/prescription/
#   POST /api/v1/doctor/consultations/{consultation_pk}/prescription/
#   GET  /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/
#   POST /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/
#   GET  /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/
#   POST /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/

urlpatterns = [
    path("", include(router.urls)),
    path("", include(consultation_router.urls)),
    path("", include(prescription_router.urls)),
]