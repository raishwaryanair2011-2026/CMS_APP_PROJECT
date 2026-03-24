from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PatientViewSet,
    BookAppointmentView,
    TodayAppointmentsView,
    AppointmentDetailView,
    BillingViewSet,
    TodayAvailableSchedulesView,
)

# -----------------------------------------------
# Router — handles ViewSets (Patient, Billing)
# -----------------------------------------------
router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'billing', BillingViewSet, basename='billing')

# -----------------------------------------------
# URL Patterns
# -----------------------------------------------
urlpatterns = [

    # ---------- Patient ----------
    # GET    /patients/               → list all active patients
    # POST   /patients/               → register new patient
    # GET    /patients/<id>/          → retrieve patient detail
    # PUT    /patients/<id>/          → full update patient
    # PATCH  /patients/<id>/          → partial update patient
    # DELETE /patients/<id>/          → soft delete patient
    # GET    /patients/?search=<q>    → search by name or phone
    *router.urls,

    # ---------- Appointments ----------
    # POST   /appointments/book/           → book appointment + billing + token
    path(
        'appointments/book/',
        BookAppointmentView.as_view(),
        name='appointment-book'
    ),

    # GET    /appointments/today/          → today's booked appointments
    # GET    /appointments/today/?schedule=<id>  → filter by doctor schedule
    path(
        'appointments/today/',
        TodayAppointmentsView.as_view(),
        name='appointment-today'
    ),

    # GET    /appointments/<id>/           → appointment detail (slip printing)
    path(
        'appointments/<int:pk>/',
        AppointmentDetailView.as_view(),
        name='appointment-detail'
    ),

    # ---------- Billing ----------
    # GET    /billing/                     → list all billing records
    # GET    /billing/<id>/                → billing detail
    # GET    /billing/?search=<q>          → search by patient name / appt code
    # GET   /billing/?patient=5
    # GET    /billing/?date=YYYY-MM-DD     → filter by date
    # (handled by router above)

    # ---------- Schedules ----------
    # GET    /schedules/today/             → doctors available right now
    path(
        'schedules/today/',
        TodayAvailableSchedulesView.as_view(),
        name='schedules-today'
    ),
]