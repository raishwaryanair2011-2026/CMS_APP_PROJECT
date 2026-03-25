from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound
from django.db import IntegrityError

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

# FIX: Import DoctorProfile from the Admin module so permission checks
# verify the full chain:
#   request.user → Staff → DoctorProfile
# rather than just checking group membership, which is not revoked
# automatically when a doctor is deactivated or soft-deleted.
from Admin.models import DoctorProfile


# ======================================================
# CUSTOM PERMISSIONS
# ======================================================

class IsDoctor(BasePermission):
    """
    Allows access only to users who have an active, non-deleted
    DoctorProfile linked through an active, non-deleted Staff record.

    This is stricter than checking group membership alone because:
    - A doctor whose Staff record is deactivated via deactivate_system()
      is automatically locked out.
    - A doctor whose DoctorProfile is soft-deleted is automatically
      locked out.
    - Group membership alone is not revoked on deactivation, so a
      group-only check would still pass for deactivated doctors.

    Chain verified:
        request.user
            → Staff (staff__user, is_active=True, is_deleted=False)
                → DoctorProfile (is_active=True, is_deleted=False)
    """

    message = "Access restricted to active doctors only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return DoctorProfile.objects.filter(
            staff__user=request.user,
            is_active=True,
            is_deleted=False,
            staff__is_active=True,
            staff__is_deleted=False,
        ).exists()


class IsDoctorOrReadOnly(BasePermission):
    """
    Allows read (GET, HEAD, OPTIONS) to any authenticated user,
    but restricts write operations to active doctors only.

    Applied to LabTestPrescriptionViewSet so that lab technicians
    can read their assigned tests via GET without being able to
    create or modify them.

    Uses the same DoctorProfile chain check as IsDoctor for writes.
    """

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    message = "Write access restricted to active doctors only."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in self.SAFE_METHODS:
            return True

        return DoctorProfile.objects.filter(
            staff__user=request.user,
            is_active=True,
            is_deleted=False,
            staff__is_active=True,
            staff__is_deleted=False,
        ).exists()


# ======================================================
# SOFT DELETE MIXIN
# ======================================================

class SoftDeleteMixin:
    """
    Overrides destroy() across all viewsets to set is_deleted=True
    instead of physically deleting the record, preserving the
    soft-delete pattern defined in TimeStampedModel.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ======================================================
# PARENT LOOKUP MIXIN
# ======================================================

class ParentLookupMixin:
    """
    Reads parent PKs injected by drf-nested-routers into self.kwargs
    and validates that the parent records actually exist and are not
    soft-deleted before scoping the child queryset.

    When a nested URL like:
        /consultations/5/prescription/3/medicines/
    is requested, drf-nested-routers injects:
        self.kwargs = {
            "consultation_pk": "5",
            "prescription_pk": "3",
            ...
        }

    Raises 404 NotFound immediately if:
        - The parent record does not exist.
        - The parent record is soft-deleted.

    This prevents returning an empty list that could be mistaken
    for "no records found" when the parent itself is invalid.
    """

    def get_consultation(self):
        consultation_pk = self.kwargs.get("consultation_pk")

        try:
            return Consultation.objects.get(
                pk=consultation_pk,
                is_deleted=False
            )
        except Consultation.DoesNotExist:
            raise NotFound(
                f"Consultation with id {consultation_pk} not found."
            )

    def get_prescription_from_kwargs(self):
        prescription_pk = self.kwargs.get("prescription_pk")
        consultation_pk = self.kwargs.get("consultation_pk")

        try:
            return Prescription.objects.get(
                pk=prescription_pk,
                consultation__id=consultation_pk,
                is_deleted=False
            )
        except Prescription.DoesNotExist:
            raise NotFound(
                f"Prescription with id {prescription_pk} not found "
                f"under consultation {consultation_pk}."
            )


# ======================================================
# CONSULTATION VIEWSET
# ======================================================

class ConsultationViewSet(SoftDeleteMixin, viewsets.ModelViewSet):
    """
    Provides CRUD for Consultation.

    URL (set by main urls.py prefix):
        GET    /api/v1/doctor/consultations/
        POST   /api/v1/doctor/consultations/
        GET    /api/v1/doctor/consultations/{id}/
        PUT    /api/v1/doctor/consultations/{id}/
        PATCH  /api/v1/doctor/consultations/{id}/
        DELETE /api/v1/doctor/consultations/{id}/   <- soft delete
    """

    serializer_class = ConsultationSerializer

    # Both IsAuthenticated and IsDoctor must pass.
    # IsAuthenticated ensures a valid session/token exists.
    # IsDoctor ensures the user has an active DoctorProfile.
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        # Consultations are top-level — no parent to scope by.
        # select_related pulls appointment and prescription in the
        # same query to avoid N+1 on list responses.
        return Consultation.objects.filter(
            is_deleted=False
        ).select_related(
            "appointment",
            "prescription",
        )

    def perform_create(self, serializer):
        # The serializer's validate_appointment() handles the expected
        # duplicate case cleanly. This try/except catches the rare race
        # condition where two simultaneous requests both pass validation
        # and both attempt to insert — the OneToOneField constraint fires
        # and we convert the IntegrityError into a clean 400.
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"appointment": "A consultation already exists for this appointment."}
            )

    def perform_update(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"detail": "Update failed due to a conflict. Please retry."}
            )


# ======================================================
# PRESCRIPTION VIEWSET
# ======================================================

class PrescriptionViewSet(SoftDeleteMixin, ParentLookupMixin, viewsets.ModelViewSet):
    """
    Provides CRUD for Prescription, nested under Consultation.

    URL:
        GET    /api/v1/doctor/consultations/{consultation_pk}/prescription/
        POST   /api/v1/doctor/consultations/{consultation_pk}/prescription/
        GET    /api/v1/doctor/consultations/{consultation_pk}/prescription/{id}/
        PUT    /api/v1/doctor/consultations/{consultation_pk}/prescription/{id}/
        PATCH  /api/v1/doctor/consultations/{consultation_pk}/prescription/{id}/
        DELETE /api/v1/doctor/consultations/{consultation_pk}/prescription/{id}/
    """

    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        # Scope to the parent consultation from the URL.
        # Raises 404 if the consultation does not exist or is deleted.
        consultation = self.get_consultation()

        return Prescription.objects.filter(
            is_deleted=False,
            consultation=consultation,
        ).select_related(
            "consultation",
        ).prefetch_related(
            "medicines",
            "medicines__medicine",
            "lab_tests",
            "lab_tests__lab_test",
        )

    def perform_create(self, serializer):
        # Retrieve and validate the parent consultation from the URL.
        # Pass it directly to save() so the client does not need to
        # send consultation in the POST body — it is derived from
        # the URL, which is the correct REST pattern.
        consultation = self.get_consultation()

        try:
            serializer.save(consultation=consultation)
        except IntegrityError:
            raise ValidationError(
                {"consultation": "A prescription already exists for this consultation."}
            )

    def perform_update(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"detail": "Update failed due to a conflict. Please retry."}
            )


# ======================================================
# MEDICINE PRESCRIPTION VIEWSET
# ======================================================

class MedicinePrescriptionViewSet(SoftDeleteMixin, ParentLookupMixin, viewsets.ModelViewSet):
    """
    Provides CRUD for MedicinePrescription, nested under Prescription.

    Doctors use this to add/update/remove individual medicines from an
    existing prescription without replacing the entire prescription.

    URL:
        GET    /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/
        POST   /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/
        GET    /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/{id}/
        PUT    /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/{id}/
        PATCH  /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/{id}/
        DELETE /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/medicines/{id}/
    """

    serializer_class = MedicinePrescriptionSerializer
    permission_classes = [IsAuthenticated, IsDoctor]

    def get_queryset(self):
        # Scope to the parent prescription AND grandparent consultation
        # from the URL kwargs.
        #
        # Without this, GET /consultations/5/prescription/3/medicines/
        # would return medicines from ALL prescriptions system-wide,
        # leaking other patients' data across the entire hospital.
        #
        # With this fix, only medicines belonging to prescription 3
        # under consultation 5 are returned.
        prescription = self.get_prescription_from_kwargs()

        return MedicinePrescription.objects.filter(
            is_deleted=False,
            prescription=prescription,
        ).select_related(
            "prescription",
            "medicine",
        )

    def perform_create(self, serializer):
        # Validates both prescription_pk and consultation_pk from the URL.
        prescription = self.get_prescription_from_kwargs()

        try:
            serializer.save(prescription=prescription)
        except IntegrityError:
            raise ValidationError(
                {"medicine": "This medicine is already prescribed in this prescription."}
            )

    def perform_update(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"detail": "Update failed due to a conflict. Please retry."}
            )

    def perform_destroy(self, instance):
        # Block deletion of a medicine that has already been dispensed
        # by the pharmacist — deleting it would create an inconsistency
        # in the pharmacy records.
        if instance.is_dispensed:
            raise ValidationError(
                {"detail": "Cannot delete a medicine that has already been dispensed."}
            )

        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])


# ======================================================
# LAB TEST PRESCRIPTION VIEWSET
# ======================================================

class LabTestPrescriptionViewSet(SoftDeleteMixin, ParentLookupMixin, viewsets.ModelViewSet):
    """
    Provides CRUD for LabTestPrescription, nested under Prescription.

    URL:
        GET    /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/
        POST   /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/
        GET    /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/{id}/
        PUT    /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/{id}/
        PATCH  /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/{id}/
        DELETE /api/v1/doctor/consultations/{consultation_pk}/prescription/{prescription_pk}/lab-tests/{id}/
    """

    serializer_class = LabTestPrescriptionSerializer

    # IsDoctorOrReadOnly allows lab technicians to read their assigned
    # tests via GET without being able to create or modify them.
    permission_classes = [IsAuthenticated, IsDoctorOrReadOnly]

    def get_queryset(self):
        # Scope to the parent prescription AND grandparent consultation.
        # Without this, GET /consultations/5/prescription/3/lab-tests/
        # would return lab tests from ALL prescriptions system-wide.
        prescription = self.get_prescription_from_kwargs()

        return LabTestPrescription.objects.filter(
            is_deleted=False,
            prescription=prescription,
        ).select_related(
            "prescription",
            "lab_test",
        )

    def perform_create(self, serializer):
        prescription = self.get_prescription_from_kwargs()

        try:
            serializer.save(prescription=prescription)
        except IntegrityError:
            raise ValidationError(
                {"lab_test": "This lab test is already prescribed in this prescription."}
            )

    def perform_update(self, serializer):
        try:
            serializer.save()
        except IntegrityError:
            raise ValidationError(
                {"detail": "Update failed due to a conflict. Please retry."}
            )

    def perform_destroy(self, instance):
        # Block deletion of a lab test that has already been billed
        # to prevent financial record inconsistencies.
        if instance.is_billed:
            raise ValidationError(
                {"detail": "Cannot delete a lab test that has already been billed."}
            )

        # Block deletion of a completed lab test — the result is part
        # of the patient's permanent medical record.
        if instance.status == LabTestPrescription.StatusChoices.COMPLETED:
            raise ValidationError(
                {"detail": "Cannot delete a completed lab test."}
            )

        instance.is_deleted = True
        instance.save(update_fields=["is_deleted", "updated_at"])