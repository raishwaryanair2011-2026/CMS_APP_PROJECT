from django.db import models

# Create your models here.

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from Admin.models import DoctorSchedule

# -------------------------
# Patient
# -------------------------
class Patient(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )

    patient_code = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=100)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.patient_code:
            year = timezone.now().year
            count = Patient.objects.filter(created_at__year=year).count() + 1
            self.patient_code = f"PAT-{year}-{str(count).zfill(4)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_code} - {self.full_name}"


# -------------------------
# Token Counter (per schedule per day)
# -------------------------
class TokenCounter(models.Model):
    schedule = models.ForeignKey(
        DoctorSchedule,
        on_delete=models.CASCADE
    )
    appointment_date = models.DateField()
    last_token = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('schedule', 'appointment_date')

    def __str__(self):
        return f"{self.schedule} | {self.appointment_date} | {self.last_token}"


# -------------------------
# Appointment
# -------------------------
class Appointment(models.Model):
    STATUS_CHOICES = (
        ('BOOKED', 'Booked'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    )

    appointment_code = models.CharField(max_length=20, unique=True, editable=False)
    appointment_date = models.DateField()
    token_no = models.PositiveIntegerField(editable=False)

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)
    schedule = models.ForeignKey(DoctorSchedule, on_delete=models.PROTECT)

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='BOOKED'
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('schedule', 'appointment_date', 'token_no')

    def clean(self):
        if self.appointment_date < timezone.now().date():
            raise ValidationError("Cannot book appointment for past date.")

    def save(self, *args, **kwargs):
        if not self.pk:
            with transaction.atomic():
                counter, _ = TokenCounter.objects.select_for_update().get_or_create(
                    schedule=self.schedule,
                    appointment_date=self.appointment_date
                )

                if counter.last_token >= 30:
                    raise ValidationError("Token limit (30) reached for this schedule.")

                counter.last_token += 1
                counter.save()

                self.token_no = counter.last_token

                date_str = self.appointment_date.strftime('%y%m%d')
                self.appointment_code = f"APT-{date_str}-{str(self.token_no).zfill(2)}"

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.appointment_code} | Token {self.token_no}"


# -------------------------
# Billing (Consultation only)
# -------------------------
class Billing(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
    )

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name='billing'
    )
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT)

    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.payment_status == 'SUCCESS' and self.paid_amount != self.total_amount:
            raise ValidationError("Full consultation fee must be paid.")

    def lock_check(self):
        if self.payment_status == 'SUCCESS':
            raise ValidationError("Paid bill cannot be modified.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Billing | {self.appointment.appointment_code}"


# -------------------------
# Consultation Bill Item
# -------------------------
class ConsultationBillItem(models.Model):
    billing = models.OneToOneField(
        Billing,
        on_delete=models.CASCADE,
        related_name='consultation_item'
    )
    fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Consultation Fee - {self.fee}"
