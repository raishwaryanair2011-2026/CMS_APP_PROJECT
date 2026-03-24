from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Patient, Appointment, Billing, ConsultationBillItem
from Admin.models import DoctorSchedule


# -------------------------
# Patient Serializer
# -------------------------
class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_code',
            'full_name',
            'dob',
            'gender',
            'phone',
            'address',
            'is_active',
            'created_at',
        ]
        read_only_fields = ('patient_code', 'created_at')


# -------------------------
# Billing Serializer (Read-Only for receptionist)
# -------------------------
class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = [
            'id',
            'appointment',
            'patient',
            'total_amount',
            'paid_amount',
            'payment_status',
            'created_at',
        ]
        read_only_fields = (
            'payment_status',
            'paid_amount',
            'created_at',
            'patient',
            'appointment',
        )


# -------------------------
# Consultation Bill Item Serializer
# -------------------------
class ConsultationBillItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationBillItem
        fields = ['id', 'billing', 'fee']
        read_only_fields = ('billing',)


# -------------------------
# Appointment with Billing Serializer
# (Receptionist Scope: Book appointment + auto-create billing)
# -------------------------
class AppointmentWithBillingSerializer(serializers.Serializer):
    appointment_date = serializers.DateField()

    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.filter(is_active=True)
    )

    consultation_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
    schedule = serializers.PrimaryKeyRelatedField(queryset=None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
        now = timezone.localtime()
        today_weekday = now.weekday()  # 0=Mon ... 6=Sun
        current_time = now.time()

        self.fields['schedule'].queryset = DoctorSchedule.objects.filter(
            day_of_week=today_weekday,
            start_time__lte=current_time,
            end_time__gte=current_time,
        )

    def validate_appointment_date(self, value):
        if value < timezone.now().date():
            raise serializers.ValidationError("Cannot book appointment for a past date.")
        return value

    def validate(self, data):
        # Re-check schedule availability at submission time,
        # not just at serializer instantiation time
        schedule = data.get('schedule')
        now = timezone.localtime()
        if not (
            schedule.day_of_week == now.weekday()
            and schedule.start_time <= now.time() <= schedule.end_time
        ):
            raise serializers.ValidationError(
                {"schedule": "This schedule is no longer available."}
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Book appointment, assign token, create billing with SUCCESS payment,
        and create consultation bill item — all in one atomic transaction.
        """
        # 1. Create Appointment
        appointment = Appointment.objects.create(
            appointment_date=validated_data['appointment_date'],
            schedule=validated_data['schedule'],
            patient=validated_data['patient'],
            status='BOOKED',
        )

        # 2. Create Billing (SUCCESS)
        # NOTE: Billing.save() calls lock_check() only when self.pk exists (update),
        # so creating with payment_status='SUCCESS' here is safe.
        # Make sure models.py Billing.save() is:
        #   if self.pk:
        #       self.lock_check()
        billing = Billing.objects.create(
            appointment=appointment,
            patient=validated_data['patient'],
            total_amount=validated_data['consultation_fee'],
            paid_amount=validated_data['consultation_fee'],
            payment_status='SUCCESS',
        )

        # 3. Create Consultation Bill Item
        ConsultationBillItem.objects.create(
            billing=billing,
            fee=validated_data['consultation_fee'],
        )

        return appointment


# -------------------------
# Appointment Serializer (for listing / viewing / slip printing)
# -------------------------
class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    billing = BillingSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'appointment_code',
            'appointment_date',
            'token_no',
            'status',
            'patient',
            'schedule',
            'billing',
            'created_at',
        ]
        read_only_fields = (
            'appointment_code',
            'token_no',
            'status',
            'billing',
            'created_at',
        )