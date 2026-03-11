from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from .models import Staff, Specialization, DoctorProfile, DoctorSchedule
from .serializers import (
    StaffSerializer,
    SpecializationSerializer,
    DoctorProfileSerializer,
    DoctorScheduleSerializer
)


# =========================================================
# STAFF VIEWSET
# =========================================================

class StaffViewSet(viewsets.ModelViewSet):

    serializer_class = StaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Staff.objects.filter(is_deleted=False)

    # CREATE STAFF
    @transaction.atomic
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        staff = serializer.save()

        return Response(
            StaffSerializer(staff).data,
            status=status.HTTP_201_CREATED
        )

    # UPDATE STAFF
    @transaction.atomic
    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)

    # SOFT DELETE STAFF
    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()
        instance.delete()

        return Response(
            {"message": "Staff deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# =========================================================
# SPECIALIZATION VIEWSET
# =========================================================

class SpecializationViewSet(viewsets.ModelViewSet):

    serializer_class = SpecializationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Specialization.objects.filter(is_deleted=False)

    # CREATE SPECIALIZATION
    @transaction.atomic
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        specialization = serializer.save()

        return Response(
            SpecializationSerializer(specialization).data,
            status=status.HTTP_201_CREATED
        )

    # SOFT DELETE SPECIALIZATION
    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()
        instance.delete()

        return Response(
            {"message": "Specialization deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )


# =========================================================
# DOCTOR PROFILE VIEWSET
# =========================================================

class DoctorProfileViewSet(viewsets.ModelViewSet):

    serializer_class = DoctorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DoctorProfile.objects.filter(is_deleted=False)

    # CREATE DOCTOR PROFILE
    @transaction.atomic
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor = serializer.save()

        return Response(
            DoctorProfileSerializer(doctor).data,
            status=status.HTTP_201_CREATED
        )

    # UPDATE DOCTOR PROFILE
    @transaction.atomic
    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)

    # SOFT DELETE DOCTOR PROFILE
    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()
        instance.delete()

        return Response(
            {"message": "Doctor profile deleted"},
            status=status.HTTP_204_NO_CONTENT
        )


# =========================================================
# DOCTOR SCHEDULE VIEWSET
# =========================================================

class DoctorScheduleViewSet(viewsets.ModelViewSet):

    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DoctorSchedule.objects.filter(is_deleted=False)

    # CREATE DOCTOR SCHEDULE
    @transaction.atomic
    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        schedule = serializer.save()

        return Response(
            DoctorScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED
        )

    # UPDATE DOCTOR SCHEDULE
    @transaction.atomic
    def update(self, request, *args, **kwargs):

        partial = kwargs.pop("partial", False)

        instance = self.get_object()

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )

        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)

    # SOFT DELETE DOCTOR SCHEDULE
    def destroy(self, request, *args, **kwargs):

        instance = self.get_object()
        instance.delete()

        return Response(
            {"message": "Schedule deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )