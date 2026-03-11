from django.db import models, transaction
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import date


# =========================================================
# BASE MODEL (Abstract)
# =========================================================

class BaseModel(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):

        if self.is_deleted:
            return

        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])


# =========================================================
# GENDER CHOICES
# =========================================================

class GenderChoices(models.TextChoices):

    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    OTHER = "OTHER", "Other"


# =========================================================
# STAFF
# =========================================================

class Staff(BaseModel):

    staff_id = models.AutoField(primary_key=True)

    staff_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_profile"
    )

    gender = models.CharField(
        max_length=10,
        choices=GenderChoices.choices
    )

    date_of_birth = models.DateField()

    phone = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^(\+91)?[6-9]\d{9}$",
                message="Enter valid Indian phone number."
            )
        ]
    )

    address = models.TextField()

    qualification = models.CharField(max_length=255)

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1000000)]
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "staff"
        ordering = ["-created_at"]

    def clean(self):

        today = date.today()

        if self.date_of_birth >= today:
            raise ValidationError("Date of birth must be in the past.")

        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) <
            (self.date_of_birth.month, self.date_of_birth.day)
        )

        if age < 21 or age > 60:
            raise ValidationError("Staff age must be between 21 and 60.")

        if not self.address or len(self.address.strip()) < 5:
            raise ValidationError("Address must contain at least 5 characters.")

        if not self.qualification or len(self.qualification.strip()) < 3:
            raise ValidationError("Qualification must contain at least 3 characters.")

        if self.qualification.strip().isdigit():
            raise ValidationError("Qualification cannot be numeric only.")

        if self.user_id and not self.is_active and self.user.is_active:
            raise ValidationError("Inactive staff cannot have active login.")

        self.address = self.address.strip()
        self.qualification = self.qualification.strip()

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        self.full_clean()
        super().save(*args, **kwargs)

        if is_new and not self.staff_code:
            self.staff_code = f"ST{str(self.staff_id).zfill(3)}"
            super().save(update_fields=["staff_code"])

    def deactivate_system(self):

        with transaction.atomic():

            self.is_active = False
            self.user.is_active = False

            self.user.save(update_fields=["is_active"])
            self.save(update_fields=["is_active", "updated_at"])

    def activate(self):

        with transaction.atomic():

            self.is_active = True
            self.user.is_active = True

            self.user.save(update_fields=["is_active"])
            self.save(update_fields=["is_active", "updated_at"])

    def __str__(self):

        return f"{self.staff_code} - {self.user.username}"


# =========================================================
# SPECIALIZATION
# =========================================================

class Specialization(BaseModel):

    specialization_id = models.AutoField(primary_key=True)

    name = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[A-Za-z\s]+$",
                message="Only letters allowed."
            )
        ]
    )

    class Meta:
        db_table = "specializations"
        ordering = ["name"]

    def clean(self):

        if not self.name or len(self.name.strip()) < 3:
            raise ValidationError("Specialization must contain at least 3 characters.")

        self.name = self.name.strip().title()

    def save(self, *args, **kwargs):

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):

        return self.name


# =========================================================
# DOCTOR PROFILE
# =========================================================

class DoctorProfile(BaseModel):

    doctor_profile_id = models.AutoField(primary_key=True)

    doctor_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    staff = models.OneToOneField(
        "administration.Staff",
        on_delete=models.PROTECT,
        related_name="doctor_profile"
    )

    specialization = models.ForeignKey(
        "administration.Specialization",
        on_delete=models.PROTECT,
        related_name="doctors"
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1000000)]
    )

    max_patient_per_day = models.PositiveIntegerField(
        default=25,
        validators=[MinValueValidator(25), MaxValueValidator(25)]
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "doctor_profiles"
        ordering = ["doctor_code"]

    def clean(self):

        if self.staff.is_deleted:
            raise ValidationError("Cannot assign doctor to deleted staff.")

        if not self.staff.is_active:
            raise ValidationError("Staff must be active.")

        if not self.staff.user.groups.filter(name="Doctor").exists():
            raise ValidationError("Staff must have Doctor role.")

        if self.specialization.is_deleted:
            raise ValidationError("Specialization is deleted.")

    def save(self, *args, **kwargs):

        is_new = self.pk is None

        self.full_clean()
        super().save(*args, **kwargs)

        if is_new and not self.doctor_code:
            self.doctor_code = f"DR{str(self.doctor_profile_id).zfill(3)}"
            super().save(update_fields=["doctor_code"])

    def __str__(self):

        return f"{self.doctor_code} - {self.staff.user.get_full_name()}"


# =========================================================
# DOCTOR SCHEDULE
# =========================================================

class DayOfWeekChoices(models.TextChoices):

    MONDAY = "MONDAY", "Monday"
    TUESDAY = "TUESDAY", "Tuesday"
    WEDNESDAY = "WEDNESDAY", "Wednesday"
    THURSDAY = "THURSDAY", "Thursday"
    FRIDAY = "FRIDAY", "Friday"
    SATURDAY = "SATURDAY", "Saturday"
    SUNDAY = "SUNDAY", "Sunday"


class DoctorSchedule(BaseModel):

    schedule_id = models.AutoField(primary_key=True)

    doctor = models.ForeignKey(
        "administration.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="schedules"
    )

    day_of_week = models.CharField(
        max_length=10,
        choices=DayOfWeekChoices.choices
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    is_active = models.BooleanField(default=True)

    class Meta:

        db_table = "doctor_schedule"

        ordering = ["doctor", "day_of_week", "start_time"]

        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "day_of_week", "start_time", "end_time"],
                condition=Q(is_deleted=False),
                name="unique_active_schedule"
            )
        ]

    def clean(self):

        if self.doctor.is_deleted or not self.doctor.is_active:
            raise ValidationError("Doctor must be active.")

        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

    def save(self, *args, **kwargs):

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):

        return f"{self.doctor.doctor_code} - {self.day_of_week}"