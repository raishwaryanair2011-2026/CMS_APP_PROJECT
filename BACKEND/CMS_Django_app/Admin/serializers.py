from rest_framework import serializers
from django.contrib.auth.models import User
from datetime import date
import re

from .models import Staff, Specialization, DoctorProfile, DoctorSchedule


# =========================================================
# USER SERIALIZER
# =========================================================

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "password"
        ]

        extra_kwargs = {
            "password": {"write_only": True},
            "email": {"required": True}
        }

    # USERNAME VALIDATION
    def validate_username(self, value):

        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Username already exists."
            )

        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must contain at least 3 characters."
            )

        return value

    # EMAIL VALIDATION
    def validate_email(self, value):

        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise serializers.ValidationError(
                "Enter a valid email address."
            )

        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(
                "Email already exists."
            )

        return value.lower()

    # PASSWORD VALIDATION
    def validate_password(self, value):

        if len(value) < 6:
            raise serializers.ValidationError(
                "Password must be at least 6 characters."
            )

        return value

    # CREATE USER
    def create(self, validated_data):

        user = User.objects.create_user(**validated_data)

        return user


# =========================================================
# STAFF SERIALIZER
# =========================================================

class StaffSerializer(serializers.ModelSerializer):

    user = UserSerializer()

    class Meta:
        model = Staff

        fields = [
            "staff_id",
            "staff_code",
            "user",
            "gender",
            "date_of_birth",
            "phone",
            "address",
            "qualification",
            "salary",
            "is_active"
        ]

        read_only_fields = ["staff_id", "staff_code"]

    # PHONE VALIDATION
    def validate_phone(self, value):

        if not re.match(r"^(\+91)?[6-9]\d{9}$", value):
            raise serializers.ValidationError(
                "Enter valid Indian phone number."
            )

        if Staff.objects.filter(phone=value, is_deleted=False).exists():
            raise serializers.ValidationError(
                "Phone number already exists."
            )

        return value

    # ADDRESS VALIDATION
    def validate_address(self, value):

        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Address must contain at least 5 characters."
            )

        return value.strip()

    # QUALIFICATION VALIDATION
    def validate_qualification(self, value):

        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Qualification must contain at least 3 characters."
            )

        if value.strip().isdigit():
            raise serializers.ValidationError(
                "Qualification cannot be numeric only."
            )

        return value.strip()

    # DATE OF BIRTH VALIDATION
    def validate_date_of_birth(self, value):

        today = date.today()

        if value >= today:
            raise serializers.ValidationError(
                "Date of birth must be in the past."
            )

        age = today.year - value.year - (
            (today.month, today.day) < (value.month, value.day)
        )

        if age < 21 or age > 60:
            raise serializers.ValidationError(
                "Staff age must be between 21 and 60."
            )

        return value

    # SALARY VALIDATION
    def validate_salary(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Salary cannot be negative."
            )

        if value > 1000000:
            raise serializers.ValidationError(
                "Salary exceeds allowed limit."
            )

        return value

    # CREATE STAFF WITH USER
    def create(self, validated_data):

        user_data = validated_data.pop("user")

        user = User.objects.create_user(**user_data)

        staff = Staff.objects.create(user=user, **validated_data)

        return staff

    # UPDATE METHOD
    def update(self, instance, validated_data):

        user_data = validated_data.pop("user", None)

        if user_data:

            user = instance.user

            for attr, value in user_data.items():

                if attr == "password":
                    user.set_password(value)
                else:
                    setattr(user, attr, value)

            user.save()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        return instance


# =========================================================
# SPECIALIZATION SERIALIZER
# =========================================================

class SpecializationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Specialization
        fields = "__all__"
        read_only_fields = ["specialization_id"]

    def validate_name(self, value):

        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Specialization must contain at least 3 characters."
            )

        if not re.match(r"^[A-Za-z\s]+$", value):
            raise serializers.ValidationError(
                "Specialization must contain only letters."
            )

        if Specialization.objects.filter(
                name__iexact=value.strip(),
                is_deleted=False
        ).exists():
            raise serializers.ValidationError(
                "Specialization already exists."
            )

        return value.strip().title()


# =========================================================
# DOCTOR PROFILE SERIALIZER
# =========================================================

class DoctorProfileSerializer(serializers.ModelSerializer):

    staff = serializers.PrimaryKeyRelatedField(
        queryset=Staff.objects.filter(is_deleted=False)
    )

    staff_details = StaffSerializer(source="staff", read_only=True)

    class Meta:
        model = DoctorProfile

        fields = [
            "doctor_profile_id",
            "doctor_code",
            "staff",
            "staff_details",
            "specialization",
            "consultation_fee",
            "max_patient_per_day",
            "is_active"
        ]

        read_only_fields = [
            "doctor_profile_id",
            "doctor_code"
        ]

    def validate_consultation_fee(self, value):

        if value < 0:
            raise serializers.ValidationError(
                "Consultation fee cannot be negative."
            )

        if value > 100000:
            raise serializers.ValidationError(
                "Consultation fee exceeds limit."
            )

        return value

    def validate(self, data):

        staff = data.get("staff")

        if DoctorProfile.objects.filter(
                staff=staff,
                is_deleted=False
        ).exists():
            raise serializers.ValidationError(
                "This staff already has a doctor profile."
            )

        return data


# =========================================================
# DOCTOR SCHEDULE SERIALIZER
# =========================================================

class DoctorScheduleSerializer(serializers.ModelSerializer):

    class Meta:
        model = DoctorSchedule

        fields = [
            "schedule_id",
            "doctor",
            "day_of_week",
            "start_time",
            "end_time",
            "is_active"
        ]

        read_only_fields = ["schedule_id"]

    def validate(self, data):

        doctor = data.get("doctor")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        day = data.get("day_of_week")

        if start_time >= end_time:
            raise serializers.ValidationError(
                "Start time must be before end time."
            )

        # Doctor active check
        if doctor.is_deleted or not doctor.is_active:
            raise serializers.ValidationError(
                "Doctor must be active."
            )

        # Overlapping schedule validation
        if DoctorSchedule.objects.filter(
            doctor=doctor,
            day_of_week=day,
            start_time__lt=end_time,
            end_time__gt=start_time,
            is_deleted=False
        ).exists():

            raise serializers.ValidationError(
                "Schedule overlaps with existing schedule."
            )

        return data