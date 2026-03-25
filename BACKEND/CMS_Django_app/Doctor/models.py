from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction
from Receptionist.models import Appointment
from Pharmacist.models import Medicine
from Lab_Technician.models import LabTest


# =====================================================
# SOFT DELETE MANAGER
# =====================================================
class SoftDeleteManager(models.Manager):
    """
    Default manager that excludes soft-deleted records.
    Use Model.all_objects.all() to include deleted records.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


# =====================================================
# BASE MODEL
# =====================================================
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    objects = SoftDeleteManager()          # filters out deleted records
    all_objects = models.Manager()         # raw access, includes deleted

    class Meta:
        abstract = True


# =====================================================
# CONSULTATION
# =====================================================
class Consultation(TimeStampedModel):

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="consultation"
    )

    symptoms = models.TextField()
    diagnosis = models.TextField()

    # FIX: Use blank=True only for TextFields, avoid null=True on text fields.
    # Empty string and NULL both mean "no value" — pick one. Django convention
    # is blank=True (empty string) for text, null=True only for non-text fields.
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["appointment"]),
        ]

    def clean(self):

        errors = {}

        # FIX: Wrap FK access in try/except. Accessing self.appointment when
        # the FK is unset raises RelatedObjectDoesNotExist (a subclass of
        # AttributeError), not a graceful validation error.
        try:
            appointment = self.appointment
        except Exception:
            errors["appointment"] = "Appointment linkage is required."
        else:
            if appointment.status == "CANCELLED":
                errors["appointment"] = (
                    "Cannot create consultation for a cancelled appointment."
                )

        if not self.symptoms or not self.symptoms.strip():
            errors["symptoms"] = "Symptoms cannot be empty."

        if not self.diagnosis or not self.diagnosis.strip():
            errors["diagnosis"] = "Diagnosis cannot be empty."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Consultation for {self.appointment.appointment_code}"


# =====================================================
# PRESCRIPTION
# =====================================================
class Prescription(TimeStampedModel):

    consultation = models.OneToOneField(
        Consultation,
        on_delete=models.CASCADE,
        related_name="prescription"
    )

    class Meta:
        indexes = [
            models.Index(fields=["consultation"])
        ]

    def clean(self):

        # FIX: Same FK access guard as Consultation.
        try:
            _ = self.consultation
        except Exception:
            raise ValidationError(
                {"consultation": "Consultation linkage is required."}
            )

    def save(self, *args, **kwargs):

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Prescription #{self.id} for {self.consultation}"


# =====================================================
# MEDICINE PRESCRIPTION
# =====================================================
class MedicinePrescription(TimeStampedModel):

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="medicines"
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT
    )

    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)
    duration = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField()
    is_dispensed = models.BooleanField(default=False)

    class Meta:
        unique_together = ["prescription", "medicine"]

        indexes = [
            models.Index(fields=["prescription"]),
            models.Index(fields=["medicine"]),
        ]

    def clean(self):

        errors = {}

        # FIX: Guard FK accesses individually so each produces a clean error.
        try:
            _ = self.prescription
        except Exception:
            errors["prescription"] = "Prescription linkage is required."

        try:
            medicine = self.medicine
            if not medicine.is_active:
                errors["medicine"] = "Inactive medicine cannot be prescribed."
        except Exception:
            errors["medicine"] = "Medicine selection is required."

        if not self.dosage or not self.dosage.strip():
            errors["dosage"] = "Dosage is required."

        if not self.frequency or not self.frequency.strip():
            errors["frequency"] = "Frequency is required."

        if not self.duration or not self.duration.strip():
            errors["duration"] = "Duration is required."

        if self.quantity is None:
            errors["quantity"] = "Quantity is required."
        elif self.quantity <= 0:
            errors["quantity"] = "Quantity must be greater than zero."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medicine.name} - {self.dosage}"


# =====================================================
# LAB TEST PRESCRIPTION
# =====================================================
class LabTestPrescription(TimeStampedModel):

    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"

    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name="lab_tests"
    )

    lab_test = models.ForeignKey(
        LabTest,
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING
    )

    # FIX: Track when the lab test was completed for audit/billing purposes.
    # Set automatically in clean() when status transitions to COMPLETED.
    completed_at = models.DateTimeField(null=True, blank=True)

    is_billed = models.BooleanField(default=False)

    class Meta:
        unique_together = ["prescription", "lab_test"]

        indexes = [
            models.Index(fields=["prescription"]),
            models.Index(fields=["lab_test"]),
        ]

    def clean(self):

        errors = {}

        try:
            _ = self.prescription
        except Exception:
            errors["prescription"] = "Prescription linkage is required."

        try:
            lab_test = self.lab_test
            if not lab_test.is_active:
                errors["lab_test"] = "Inactive lab test cannot be prescribed."
        except Exception:
            errors["lab_test"] = "Lab test selection is required."

        if not self.status:
            errors["status"] = "Status is required."

        if errors:
            raise ValidationError(errors)

        # FIX: Auto-stamp completed_at when status transitions to COMPLETED.
        # Only set it once — don't overwrite if already stamped.
        if self.status == self.StatusChoices.COMPLETED and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()

        # FIX: Clear completed_at if status is rolled back to PENDING.
        if self.status == self.StatusChoices.PENDING:
            self.completed_at = None

    def save(self, *args, **kwargs):

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.lab_test.name} - {self.status}"