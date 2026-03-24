from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView, ListAPIView  
from rest_framework.filters import SearchFilter
# from rest_framework.permissions import IsAuthenticated, AllowAny   

from .models import Patient, Appointment, Billing
from .serializers import (
    PatientSerializer,
    AppointmentSerializer,
    BillingSerializer,
    AppointmentWithBillingSerializer,
)
from Admin.models import DoctorSchedule
from Admin.serializers import DoctorScheduleSerializer


# ---------------------------------------
# Patient ViewSet
# ---------------------------------------
class PatientViewSet(viewsets.ModelViewSet):
    """
    Handles:
    - Patient registration
    - Patient listing
    - Patient search (name / phone)
    - Update patient
    - Soft delete patient
    """

    # permission_classes = [IsAuthenticated] 
    serializer_class = PatientSerializer
    filter_backends = [SearchFilter]
    search_fields = ['full_name', 'phone']

    def get_queryset(self):
        return Patient.objects.filter(is_active=True).order_by('-created_at')

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete — sets is_active=False instead of hard delete.
        The base model's delete() does the same, but this keeps
        the response message explicit for the receptionist.
        """
        patient = self.get_object()
        patient.is_active = False
        patient.save()
        return Response(
            {"message": "Patient deactivated successfully"},
            status=status.HTTP_200_OK
        )


# ---------------------------------------
# Appointment Booking
# ---------------------------------------
class BookAppointmentView(APIView):
    """
    Single endpoint that atomically:
    - Books appointment + assigns token
    - Creates billing (SUCCESS)
    - Creates consultation bill item
    """

    # permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AppointmentWithBillingSerializer(data=request.data)

        if serializer.is_valid():
            appointment = serializer.save()
            return Response(
                AppointmentSerializer(appointment).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------
# Today's Appointments
# ---------------------------------------
class TodayAppointmentsView(APIView):
    """
    View today's booked appointments.
    Optional filter: ?schedule=<id>
    """

    # permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()

        queryset = Appointment.objects.filter(
            appointment_date=today,
            status='BOOKED'
        ).select_related('patient', 'schedule', 'billing')

        schedule_id = request.query_params.get('schedule')
        if schedule_id:
            queryset = queryset.filter(schedule_id=schedule_id)

        serializer = AppointmentSerializer(queryset, many=True)
        return Response(serializer.data)


# ---------------------------------------
# Appointment Detail (Slip Printing)
# ---------------------------------------
class AppointmentDetailView(RetrieveAPIView):
    """
    Returns full appointment detail for slip printing.
    """

    # permission_classes = [IsAuthenticated]      
    serializer_class = AppointmentSerializer
    queryset = Appointment.objects.select_related(
        'patient',
        'schedule',
        'billing'
    )


# ---------------------------------------
# Billing ViewSet (Read Only)
# ---------------------------------------
class BillingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Receptionist can VIEW billing only.
    Supports:
    - Search by patient name or appointment code
    - Filter by date: ?date=YYYY-MM-DD
    """

    # permission_classes = [IsAuthenticated]
    serializer_class = BillingSerializer
    filter_backends = [SearchFilter]
    search_fields = ['patient__full_name', 'appointment__appointment_code']

    def get_queryset(self):
        queryset = Billing.objects.select_related(
            'appointment', 'patient'
        ).order_by('-created_at')

        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(created_at__date=date)

        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        return queryset


# ---------------------------------------
# Today's Available Doctor Schedules
# ---------------------------------------
class TodayAvailableSchedulesView(ListAPIView):
    """
    Returns doctor schedules active RIGHT NOW today.
    Public endpoint — used by receptionist booking form
    to populate the schedule dropdown.
    """

    serializer_class = DoctorScheduleSerializer
    # permission_classes = [AllowAny]

    def get_queryset(self):
        now = timezone.localtime()
        today_weekday = now.weekday()
        current_time = now.time()

        return DoctorSchedule.objects.filter(
            day_of_week=today_weekday,
            start_time__lte=current_time,
            end_time__gte=current_time,
        )