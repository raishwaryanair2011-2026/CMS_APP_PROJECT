from rest_framework import serializers
from django.db import transaction

from .models import (
    Consultation,
    Prescription,
    MedicinePrescription,
    LabTestPrescription
)

from Receptionist.models import Appointment
from Pharmacist.models import Medicine
from Lab_Technician.models import LabTest


# ======================================================
# MEDICINE PRESCRIPTION SERIALIZER
# ======================================================

class MedicinePrescriptionSerializer(serializers.ModelSerializer):

    medicine_name = serializers.CharField(
        source="medicine.name",
        read_only=True
    )

    class Meta:
        model = MedicinePrescription

        fields = [
            "id",
            "prescription",
            "medicine",
            "medicine_name",
            "dosage",
            "frequency",
            "duration",
            "quantity",
            "is_dispensed",
        ]

        # FIX: Mark 'prescription' as read_only so clients cannot pass an
        # arbitrary prescription ID and link medicines to someone else's
        # prescription. The prescription is always set programmatically by the
        # parent PrescriptionSerializer.create() or by the view's
        # perform_create() context.
        # Also mark 'is_dispensed' read_only — only the pharmacist module
        # should be able to flip this flag, not the doctor.
        read_only_fields = ["id", "prescription", "is_dispensed"]

    def validate_medicine(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "Inactive medicine cannot be prescribed."
            )

        return value

    def validate_quantity(self, value):

        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )

        return value


# ======================================================
# LAB TEST PRESCRIPTION SERIALIZER
# ======================================================

class LabTestPrescriptionSerializer(serializers.ModelSerializer):

    lab_test_name = serializers.CharField(
        source="lab_test.name",
        read_only=True
    )

    class Meta:
        model = LabTestPrescription

        fields = [
            "id",
            "prescription",
            "lab_test",
            "lab_test_name",
            "status",
            "completed_at",
            "is_billed",
        ]

        # FIX: Same as MedicinePrescriptionSerializer — 'prescription' must be
        # read_only to prevent clients from pointing lab tests at arbitrary
        # prescriptions.
        # 'is_billed' is read_only — only the billing/pharmacist module should
        # set this.
        # 'completed_at' is read_only — set automatically by the model's
        # clean() when status transitions to COMPLETED.
        read_only_fields = ["id", "prescription", "completed_at", "is_billed"]

    def validate_lab_test(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "Inactive lab test cannot be prescribed."
            )

        return value

    def validate_status(self, value):

        # FIX: Validate that status is one of the defined choices.
        valid = [choice[0] for choice in LabTestPrescription.StatusChoices.choices]

        if value not in valid:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid)}."
            )

        return value


# ======================================================
# PRESCRIPTION SERIALIZER
# ======================================================

class PrescriptionSerializer(serializers.ModelSerializer):

    medicines = MedicinePrescriptionSerializer(
        many=True,
        required=False
    )

    lab_tests = LabTestPrescriptionSerializer(
        many=True,
        required=False
    )

    class Meta:
        model = Prescription

        fields = [
            "id",
            "consultation",
            "medicines",
            "lab_tests",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_consultation(self, value):

        # FIX: Move duplicate prescription check from the view into the
        # serializer so it is enforced on any programmatic usage (management
        # commands, tests, signals) — not just HTTP requests.
        # The view still catches IntegrityError as a safety net for race
        # conditions, but this check handles the clean/expected case.
        if Prescription.objects.filter(consultation=value).exists():
            raise serializers.ValidationError(
                "A prescription already exists for this consultation."
            )

        return value

    def create(self, validated_data):

        medicines_data = validated_data.pop("medicines", [])
        lab_tests_data = validated_data.pop("lab_tests", [])

        with transaction.atomic():

            prescription = Prescription.objects.create(**validated_data)

            for med in medicines_data:

                # FIX: Pop 'prescription' key from the nested payload in case
                # the client mistakenly included it. Without this, Django raises
                # TypeError: got multiple values for argument 'prescription'.
                med.pop("prescription", None)

                MedicinePrescription.objects.create(
                    prescription=prescription,
                    **med
                )

            for lab in lab_tests_data:

                # FIX: Same defensive pop for lab test payloads.
                lab.pop("prescription", None)

                LabTestPrescription.objects.create(
                    prescription=prescription,
                    **lab
                )

        return prescription

    def update(self, instance, validated_data):

        # FIX: Implement update() so PATCH/PUT requests on a prescription
        # can also update its nested medicines and lab tests.
        # Strategy:
        #   - For medicines: full replace — delete existing, recreate from payload.
        #   - For lab tests: full replace — delete existing, recreate from payload.
        # This is the simplest safe strategy. If partial updates per item are
        # needed later, switch to a merge strategy keyed on medicine/lab_test ID.

        medicines_data = validated_data.pop("medicines", None)
        lab_tests_data = validated_data.pop("lab_tests", None)

        with transaction.atomic():

            # Update scalar fields on the prescription itself.
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            if medicines_data is not None:
                instance.medicines.all().delete()

                for med in medicines_data:
                    med.pop("prescription", None)
                    MedicinePrescription.objects.create(
                        prescription=instance,
                        **med
                    )

            if lab_tests_data is not None:
                instance.lab_tests.all().delete()

                for lab in lab_tests_data:
                    lab.pop("prescription", None)
                    LabTestPrescription.objects.create(
                        prescription=instance,
                        **lab
                    )

        return instance


# ======================================================
# CONSULTATION SERIALIZER
# ======================================================

class ConsultationSerializer(serializers.ModelSerializer):

    appointment_code = serializers.CharField(
        source="appointment.appointment_code",
        read_only=True
    )

    # FIX: Expose the nested prescription as a read-only field so that
    # GET /consultations/{id}/ returns the full prescription detail
    # without requiring a separate API call.
    prescription = PrescriptionSerializer(read_only=True)

    class Meta:
        model = Consultation

        fields = [
            "id",
            "appointment",
            "appointment_code",
            "symptoms",
            "diagnosis",
            "notes",
            "prescription",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_appointment(self, value):

        if value.status == "CANCELLED":
            raise serializers.ValidationError(
                "Cannot create consultation for a cancelled appointment."
            )

        # FIX: Move duplicate consultation check from the view into the
        # serializer so it is enforced on any programmatic usage, not just
        # HTTP requests. The view still catches IntegrityError as a safety
        # net for race conditions.
        if Consultation.objects.filter(appointment=value).exists():
            raise serializers.ValidationError(
                "A consultation already exists for this appointment."
            )

        return value

    def validate(self, data):

        # FIX: Object-level validation — ensure symptoms and diagnosis are not
        # blank strings (field-level validators only check presence, not content
        # after stripping whitespace).
        if "symptoms" in data and not data["symptoms"].strip():
            raise serializers.ValidationError(
                {"symptoms": "Symptoms cannot be blank."}
            )

        if "diagnosis" in data and not data["diagnosis"].strip():
            raise serializers.ValidationError(
                {"diagnosis": "Diagnosis cannot be blank."}
            )

        return data