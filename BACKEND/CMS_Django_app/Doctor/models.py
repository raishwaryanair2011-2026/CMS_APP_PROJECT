# from django.db import models
# from django.core.exceptions import ValidationError
# from Receptionist.models import Appointment
# from Pharmacist import Medicine
# from Lab_Technician import LabTest

# class TimeStampedModel(models.Model):
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         abstract = True

# # =====================================================
# # DOCTOR OPERATIONS: CONSULTATION & PRESCRIPTIONS
# # =====================================================
# class Consultation(TimeStampedModel):
#     appointment = models.OneToOneField(
#         Appointment, 
#         on_delete=models.CASCADE, 
#         related_name='consultation'
#     )
#     symptoms = models.TextField()
#     diagnosis = models.TextField()
#     notes = models.TextField(blank=True, null=True) 

#     def clean(self):
#         errors = {}

#         if not hasattr(self, 'appointment') or self.appointment is None:
#             errors['appointment'] = "Appointment linkage is required."
#         elif self.appointment.status == 'CANCELLED':
#             errors['appointment'] = "Cannot create a consultation for a cancelled appointment."

#         if not self.symptoms or not str(self.symptoms).strip():
#             errors['symptoms'] = "Symptoms cannot be empty."
            
#         if not self.diagnosis or not str(self.diagnosis).strip():
#             errors['diagnosis'] = "Diagnosis cannot be empty."

#         if errors:
#             raise ValidationError(errors)

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"Consultation for {self.appointment.appointment_code if hasattr(self, 'appointment') else 'Unknown'}"

# class Prescription(TimeStampedModel):
#     consultation = models.OneToOneField(
#         Consultation, 
#         on_delete=models.CASCADE, 
#         related_name='prescription'
#     )

#     def clean(self):
#         if not hasattr(self, 'consultation') or self.consultation is None:
#             raise ValidationError({"consultation": "Consultation linkage is required."})

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"Prescription #{self.id} for {self.consultation}"

# # =====================================================
# # MEDICINE MAPPING
# # # =====================================================
# # class Medicine(models.Model):
# #     name = models.CharField(max_length=255)
# #     is_active = models.BooleanField(default=True)

# #     def clean(self):
# #         if not self.name or not str(self.name).strip():
# #             raise ValidationError({"name": "Medicine name is required."})

# #     def save(self, *args, **kwargs):
# #         self.full_clean()
# #         super().save(*args, **kwargs)

# #     def __str__(self):
# #         return self.name

# class MedicinePrescription(models.Model):
#     prescription = models.ForeignKey(
#         Prescription, 
#         on_delete=models.CASCADE, 
#         related_name='medicines'
#     )
#     medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
#     dosage = models.CharField(max_length=50)       
#     frequency = models.CharField(max_length=50)    
#     duration = models.CharField(max_length=50)     
#     quantity = models.IntegerField()               
#     is_dispensed = models.BooleanField(default=False)

#     def clean(self):
#         errors = {}

#         if not hasattr(self, 'prescription') or self.prescription is None:
#             errors['prescription'] = "Prescription linkage is required."

#         if not hasattr(self, 'medicine') or self.medicine is None:
#             errors['medicine'] = "Medicine selection is required."
#         elif not self.medicine.is_active:
#             errors['medicine'] = "Cannot prescribe an inactive medicine."

#         # 2. Required Text Fields Validation
#         if not self.dosage or not str(self.dosage).strip():
#             errors['dosage'] = "Dosage is required."
            
#         if not self.frequency or not str(self.frequency).strip():
#             errors['frequency'] = "Frequency is required."
            
#         if not self.duration or not str(self.duration).strip():
#             errors['duration'] = "Duration is required."

#         if self.quantity is None:
#             errors['quantity'] = "Quantity is required."
#         elif self.quantity <= 0:
#             errors['quantity'] = "Quantity must be greater than zero."

#         if errors:
#             raise ValidationError(errors)

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.medicine.name if hasattr(self, 'medicine') else 'Unknown'} - {self.dosage}"

# # =====================================================
# # LAB MAPPING
# # =====================================================
# # class LabTest(models.Model):
# #     name = models.CharField(max_length=255)
# #     is_active = models.BooleanField(default=True)

# #     def clean(self):
# #         if not self.name or not str(self.name).strip():
# #             raise ValidationError({"name": "Lab test name is required."})

# #     def save(self, *args, **kwargs):
# #         self.full_clean()
# #         super().save(*args, **kwargs)

# #     def __str__(self):
# #         return self.name

# class LabTestPrescription(models.Model):
#     class StatusChoices(models.TextChoices):
#         PENDING = 'PENDING', 'Pending'
#         COMPLETED = 'COMPLETED', 'Completed'

#     prescription = models.ForeignKey(
#         Prescription, 
#         on_delete=models.CASCADE, 
#         related_name='lab_tests'
#     )
#     lab_test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
#     status = models.CharField(
#         max_length=20, 
#         choices=StatusChoices.choices, 
#         default=StatusChoices.PENDING
#     )
#     is_billed = models.BooleanField(default=False)

#     def clean(self):
#         errors = {}

#         if not hasattr(self, 'prescription') or self.prescription is None:
#             errors['prescription'] = "Prescription linkage is required."

#         if not hasattr(self, 'lab_test') or self.lab_test is None:
#             errors['lab_test'] = "Lab test selection is required."
#         elif not self.lab_test.is_active:
#             errors['lab_test'] = "Cannot prescribe an inactive lab test."

#         if not self.status or not str(self.status).strip():
#             errors['status'] = "Status is required."

#         if errors:
#             raise ValidationError(errors)

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"{self.lab_test.name if hasattr(self, 'lab_test') else 'Unknown'} - {self.status}"

from django.db import models
from django.core.exceptions import ValidationError
from django.db import transaction
from Receptionist.models import Appointment
from Pharmacist.models import Medicine
from Lab_Technician.models import LabTest


# =====================================================
# BASE MODEL
# =====================================================
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

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
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["appointment"]),
        ]

    def clean(self):

        errors = {}

        if not self.appointment:
            errors["appointment"] = "Appointment linkage is required."

        elif self.appointment.status == "CANCELLED":
            errors["appointment"] = "Cannot create consultation for cancelled appointment."

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

        if not self.consultation:
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
            models.Index(fields=["medicine"])
        ]

    def clean(self):

        errors = {}

        if not self.prescription:
            errors["prescription"] = "Prescription linkage is required."

        if not self.medicine:
            errors["medicine"] = "Medicine selection is required."

        elif not self.medicine.is_active:
            errors["medicine"] = "Inactive medicine cannot be prescribed."

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

    is_billed = models.BooleanField(default=False)

    class Meta:

        unique_together = ["prescription", "lab_test"]

        indexes = [
            models.Index(fields=["prescription"]),
            models.Index(fields=["lab_test"])
        ]

    def clean(self):

        errors = {}

        if not self.prescription:
            errors["prescription"] = "Prescription linkage is required."

        if not self.lab_test:
            errors["lab_test"] = "Lab test selection is required."

        elif not self.lab_test.is_active:
            errors["lab_test"] = "Inactive lab test cannot be prescribed."

        if not self.status:
            errors["status"] = "Status is required."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        self.full_clean()

        with transaction.atomic():
            super().save(*args, **kwargs)

    def __str__(self):

        return f"{self.lab_test.name} - {self.status}"