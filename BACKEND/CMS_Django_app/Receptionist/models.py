from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from Admin.models import DoctorSchedule


# =====================================================
# BASE MODEL (Soft Delete + Timestamp)
# =====================================================

class TimeStampedSoftDeleteModel(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_active = False
        self.save()


# =====================================================
# PATIENT
# =====================================================

class Patient(TimeStampedSoftDeleteModel):

    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    phone_validator = RegexValidator(
        regex=r'^\+?[0-9]{10,15}$',
        message="Enter a valid phone number."
    )

    patient_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    full_name = models.CharField(max_length=100)

    dob = models.DateField(null=True, blank=True)

    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    phone = models.CharField(
        max_length=15,
        validators=[phone_validator]
    )

    address = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def generate_patient_code(self):
        with transaction.atomic():
            year = timezone.now().year
            last = (
                Patient.objects
                .select_for_update()
                .filter(patient_code__startswith=f"PAT-{year}")
                .order_by("-id")
                .first()
            )
            number = int(last.patient_code.split("-")[-1]) + 1 if last else 1
            return f"PAT-{year}-{str(number).zfill(4)}"

    def clean(self):

        errors = {}

        if self.dob:

            today = timezone.now().date()

            if self.dob > today:
                errors["dob"] = "Date of birth cannot be in the future."

            age = (today - self.dob).days / 365.25

            if age > 120:
                errors["dob"] = "Invalid age."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if not self.patient_code:
                self.patient_code = self.generate_patient_code()
            self.full_clean()
            super().save(*args, **kwargs)

    def __str__(self):

        return f"{self.patient_code} - {self.full_name}"


# =====================================================
# TOKEN COUNTER
# =====================================================

class TokenCounter(models.Model):

    schedule = models.ForeignKey(
        DoctorSchedule,
        on_delete=models.CASCADE
    )

    appointment_date = models.DateField()

    last_token = models.PositiveIntegerField(default=0)

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "appointment_date"],
                name="unique_token_per_schedule_day"
            )
        ]

    def __str__(self):

        return f"{self.schedule} | {self.appointment_date} | {self.last_token}"


# =====================================================
# APPOINTMENT
# =====================================================

class Appointment(TimeStampedSoftDeleteModel):

    STATUS_CHOICES = (
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    )

    appointment_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    appointment_date = models.DateField()

    token_no = models.PositiveIntegerField(editable=False)

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT
    )

    schedule = models.ForeignKey(
        DoctorSchedule,
        on_delete=models.PROTECT
    )

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='BOOKED'
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "appointment_date", "token_no"],
                name="unique_token_per_schedule"
            )
        ]

    def clean(self):

        if self.appointment_date < timezone.now().date():
            raise ValidationError(
                {"appointment_date": "Cannot book appointment for past date."}
            )

        if not self.patient.is_active:
            raise ValidationError(
                {"patient": "Inactive patient cannot book appointment."}
            )

    def generate_appointment_code(self):
        date_str = self.appointment_date.strftime('%y%m%d')
        schedule_id = str(self.schedule_id).zfill(3)
        return f"APT-{date_str}-{schedule_id}-{str(self.token_no).zfill(2)}"

    def save(self, *args, **kwargs):

        if not self.pk:

            self.full_clean()
            with transaction.atomic():

                counter, _ = TokenCounter.objects.select_for_update().get_or_create(
                    schedule=self.schedule,
                    appointment_date=self.appointment_date
                )

                if counter.last_token >= 30:
                    raise ValidationError(
                        "Token limit (30) reached for this schedule."
                    )

                counter.last_token += 1
                counter.save()

                self.token_no = counter.last_token

                self.appointment_code = self.generate_appointment_code()


        super().save(*args, **kwargs)

    def __str__(self):

        return f"{self.appointment_code} | Token {self.token_no}"


# =====================================================
# BILLING
# =====================================================

class Billing(TimeStampedSoftDeleteModel):

    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
    )

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name='billing'
    )

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT
    )

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )
        
    def clean(self):

        errors = {}

        if self.total_amount <= 0:
            errors["total_amount"] = "Total amount must be greater than zero."

        if self.paid_amount < 0:
            errors["paid_amount"] = "Paid amount cannot be negative."

        if self.payment_status == 'SUCCESS':

            if self.paid_amount != self.total_amount:
                errors["paid_amount"] = "Full consultation fee must be paid."

        if errors:
            raise ValidationError(errors)

    def lock_check(self):

        if self.payment_status == 'SUCCESS':
            raise ValidationError("Paid bill cannot be modified.")

    def save(self, *args, **kwargs):
        if self.pk:
            self.lock_check()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):

        return f"Billing | {self.appointment.appointment_code}"


# =====================================================
# CONSULTATION BILL ITEM
# =====================================================

class ConsultationBillItem(TimeStampedSoftDeleteModel):

    billing = models.OneToOneField(
        Billing,
        on_delete=models.CASCADE,
        related_name='consultation_item'
    )

    fee = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):

        if self.fee <= 0:
            raise ValidationError(
                {"fee": "Consultation fee must be greater than zero."}
            )

    def save(self, *args, **kwargs):

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):

        return f"Consultation Fee - {self.fee}"