from django.db import models

# Create your models here.


from django.db import models
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils import timezone


# =====================================
# STAFF MODEL (Linked to Django User)
# =====================================

class Staff(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=15)
    joining_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "Staff"

    def clean(self):
        if not self.full_name:
            raise ValidationError("Full name is mandatory")

        if not self.phone.isdigit():
            raise ValidationError("Phone must contain only digits")

        if len(self.phone) < 10:
            raise ValidationError("Phone must be at least 10 digits")

        if self.joining_date > timezone.now().date():
            raise ValidationError("Joining date cannot be in future")

    def __str__(self):
        return self.full_name


# =====================================
# SPECIALIZATION MODEL
# =====================================

class Specialization(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "Specialization"

    def __str__(self):
        return self.name


# =====================================
# DOCTOR PROFILE MODEL
# =====================================

class DoctorProfile(models.Model):
    doctor_code = models.CharField(max_length=20, unique=True)
    staff = models.OneToOneField(Staff, on_delete=models.CASCADE)
    specialization = models.ForeignKey(Specialization, on_delete=models.PROTECT)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "DoctorProfile"

    def clean(self):
        if self.consultation_fee <= 0:
            raise ValidationError("Consultation fee must be positive")

        # Ensure staff belongs to Doctor group
        if not self.staff.user.groups.filter(name="Doctor").exists():
            raise ValidationError("Assigned staff is not in Doctor role")

    def __str__(self):
        return f"{self.staff.full_name} - {self.specialization.name}"


# =====================================
# DOCTOR SCHEDULE MODEL
# =====================================

class DoctorSchedule(models.Model):
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()  # 0=Sun ... 6=Sat
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        db_table = "DoctorSchedule"
        unique_together = ('doctor', 'day_of_week')

    def clean(self):
        if self.day_of_week < 0 or self.day_of_week > 6:
            raise ValidationError("Day of week must be between 0 and 6")

        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be earlier than end time")

    def __str__(self):
        return f"{self.doctor.staff.full_name} - Day {self.day_of_week}"
