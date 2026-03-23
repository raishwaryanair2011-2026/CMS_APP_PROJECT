from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from .models import (
    Consultation,
    Prescription,
    MedicinePrescription,
    LabTestPrescription
)

from .serializers import (
    ConsultationSerializer,
    PrescriptionSerializer,
    MedicinePrescriptionSerializer,
    LabTestPrescriptionSerializer
)

from Receptionist.models import Appointment


# ======================================================
# CONSULTATION VIEWSET
# ======================================================

class ConsultationViewSet(viewsets.ModelViewSet):

    queryset = Consultation.objects.filter(is_deleted=False)

    serializer_class = ConsultationSerializer

    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        appointment = serializer.validated_data.get("appointment")

        if Consultation.objects.filter(appointment=appointment).exists():
            raise ValidationError(
                "Consultation already exists for this appointment."
            )

        serializer.save()


# ======================================================
# PRESCRIPTION VIEWSET
# ======================================================

class PrescriptionViewSet(viewsets.ModelViewSet):

    queryset = Prescription.objects.filter(is_deleted=False)

    serializer_class = PrescriptionSerializer

    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        consultation = serializer.validated_data.get("consultation")

        if Prescription.objects.filter(consultation=consultation).exists():
            raise ValidationError(
                "Prescription already exists for this consultation."
            )

        serializer.save()


# ======================================================
# MEDICINE PRESCRIPTION VIEWSET
# ======================================================

class MedicinePrescriptionViewSet(viewsets.ModelViewSet):

    queryset = MedicinePrescription.objects.filter(is_deleted=False)

    serializer_class = MedicinePrescriptionSerializer

    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        prescription = serializer.validated_data.get("prescription")

        medicine = serializer.validated_data.get("medicine")

        if MedicinePrescription.objects.filter(
                prescription=prescription,
                medicine=medicine
        ).exists():

            raise ValidationError(
                "This medicine is already prescribed."
            )

        serializer.save()


# ======================================================
# LAB TEST PRESCRIPTION VIEWSET
# ======================================================

class LabTestPrescriptionViewSet(viewsets.ModelViewSet):

    queryset = LabTestPrescription.objects.filter(is_deleted=False)

    serializer_class = LabTestPrescriptionSerializer

    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):

        prescription = serializer.validated_data.get("prescription")

        lab_test = serializer.validated_data.get("lab_test")

        if LabTestPrescription.objects.filter(
                prescription=prescription,
                lab_test=lab_test
        ).exists():

            raise ValidationError(
                "This lab test is already prescribed."
            )

        serializer.save()