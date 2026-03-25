from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
# from django.db.models import Sum, Count

from .models import (
    MedicineCategory,Medicine,MedicineBatch,MedicineDispense,PharmacyBillItem,
)
from .serializers import (
    MedicineCategorySerializer,
    MedicineSerializer,
    MedicineBatchSerializer,
    MedicineDispenseSerializer,
    PharmacyBillItemSerializer,
    MedicinePrescriptionReadSerializer,
)
from doctor.models import MedicinePrescription


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    return Response({
        "success": True,
        "message": message,
        "data":    data,
    }, status=status_code)

def error_response(message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({
        "success": False,
        "message": message,
        "errors":  errors,
    }, status=status_code)



class MedicineCategoryViewSet(viewsets.ModelViewSet):
  
    queryset   = MedicineCategory.objects.all()
    serializer_class  = MedicineCategorySerializer
    authentication_classes = []
    permission_classes   = [AllowAny]

    def list(self, request, *args, **kwargs):
        queryset   = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Medicine categories retrieved successfully."
        )

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Medicine category retrieved successfully."
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Medicine category created successfully.",
                status_code=status.HTTP_201_CREATED
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def update(self, request, *args, **kwargs):
        partial    = kwargs.pop("partial", False)
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Medicine category updated successfully."
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # soft delete from TimeStampedSoftDeleteModel
        return success_response(
            message="Medicine category deleted successfully."
        )
    

class PharmacistDashboardView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()

        # Low stock medicines
        all_medicines = Medicine.objects.filter(is_deleted=False)
        low_stock_count = sum(1 for m in all_medicines if m.needs_reorder)

        # Expiring batches within 30 days
        threshold = today + timedelta(days=30)
        expiring_soon_count = MedicineBatch.objects.filter(
            expiry_date__lte=threshold,
            is_active=True,
            is_deleted=False
        ).count()

        # Pending prescriptions (not yet dispensed)
        pending_prescriptions_count = MedicinePrescription.objects.filter(
            is_dispensed=False
        ).count()

        # Today's dispenses
        todays_dispense_count = MedicineDispense.objects.filter(
            dispensed_at__date=today
        ).count()

        # Total medicines and active batches
        total_medicines = Medicine.objects.filter(is_deleted=False).count()
        total_active_batches = MedicineBatch.objects.filter(
            is_active=True,
            is_deleted=False
        ).count()

        return Response({
            "success": True,
            "message": "Dashboard data retrieved successfully.",
            "data": {
                "low_stock_medicines":        low_stock_count,
                "expiring_soon_batches":      expiring_soon_count,
                "pending_prescriptions":      pending_prescriptions_count,
                "todays_dispenses":           todays_dispense_count,
                "total_medicines":            total_medicines,
                "total_active_batches":       total_active_batches,
            }
        })


class MedicineViewSet(viewsets.ModelViewSet):
    
    serializer_class       = MedicineSerializer
    authentication_classes = []
    permission_classes     = [AllowAny]

    def get_queryset(self):
        queryset = Medicine.objects.select_related("category").all()

        # filter by category
        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # filter by is_active
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # needs_reorder is a @property — filter in Python not DB
        needs_reorder = request.query_params.get("needs_reorder")
        if needs_reorder and needs_reorder.lower() == "true":
            queryset = [m for m in queryset if m.needs_reorder]

        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Medicines retrieved successfully."
        )

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Medicine retrieved successfully."
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Medicine added successfully.",
                status_code=status.HTTP_201_CREATED
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def update(self, request, *args, **kwargs):
        partial    = kwargs.pop("partial", False)
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Medicine updated successfully."
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # soft delete
        return success_response(
            message="Medicine deleted successfully."
        )



class MedicineBatchViewSet(viewsets.ModelViewSet):
   
    serializer_class    = MedicineBatchSerializer
    authentication_classes = []
    permission_classes   = [AllowAny]

    def get_queryset(self):
        from django.utils import timezone
        from datetime import timedelta

        queryset = MedicineBatch.objects.select_related("medicine").all()

        # filter by medicine
        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)

        # filter by is_active
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        # filter batches expiring within 30 days
        expiring_soon = self.request.query_params.get("expiring_soon")
        if expiring_soon and expiring_soon.lower() == "true":
            threshold = timezone.now().date() + timedelta(days=30)
            queryset  = queryset.filter(
                expiry_date__lte=threshold,
                is_active=True
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset   = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Batches retrieved successfully."
        )

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Batch retrieved successfully."
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Batch added successfully.",
                status_code=status.HTTP_201_CREATED
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def update(self, request, *args, **kwargs):
        # medicine and batch_no are locked in serializer update()
        partial    = kwargs.pop("partial", False)
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Batch updated successfully."
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # soft delete
        return success_response(
            message="Batch deleted successfully."
        )



class PrescriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET only, no POST/PUT/PATCH/DELETE
    GET /prescriptions/pending/  → pending (not dispensed) prescriptions
    GET /prescriptions/<id>/     → single prescription detail
    """
    serializer_class  = MedicinePrescriptionReadSerializer
    authentication_classes = []
    permission_classes  = [AllowAny]

    def get_queryset(self):
        queryset = MedicinePrescription.objects.select_related(
            "medicine",
            "prescription__consultation__appointment__patient"
        ).all()

        # filter by patient name
        patient = self.request.query_params.get("patient")
        if patient:
            queryset = queryset.filter(
                prescription__consultation__appointment__patient__full_name__icontains=patient
            )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset   = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Prescriptions retrieved successfully."
        )

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Prescription retrieved successfully."
        )

    # Custom action 
    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        """
        Returns only prescriptions that are not yet dispensed.
        """
        queryset = self.get_queryset().filter(is_dispensed=False)
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Pending prescriptions retrieved successfully."
        )



class MedicineDispenseViewSet(viewsets.ModelViewSet):
    """
    POST triggers (inside model save()):
    1. Creates MedicineDispense record
    2. Generates dispense_code
    3. Deducts stock from MedicineBatch
    4. Auto deactivates batch if stock = 0
    5. Flips MedicinePrescription.is_dispensed = True
    """
    # update and destroy are disabled — dispense records are immutable 
    serializer_class       = MedicineDispenseSerializer
    authentication_classes = []
    permission_classes     = [AllowAny]

    def get_queryset(self):
        return MedicineDispense.objects.select_related(
            "medicine_prescription__medicine",
            "medicine_batch__medicine",
            "dispensed_by"
        ).all()

    def list(self, request, *args, **kwargs):
        queryset   = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Dispense records retrieved successfully."
        )

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Dispense record retrieved successfully."
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Medicine dispensed successfully.",
                status_code=status.HTTP_201_CREATED
            )
        return error_response(
            message="Dispensing failed.",
            errors=serializer.errors
        )

    # Disabled — dispense records are immutable
    def update(self, request, *args, **kwargs):
        return error_response(
            message="Dispense records cannot be updated.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    # Disabled — dispense records cannot be deleted
    def destroy(self, request, *args, **kwargs):
        return error_response(
            message="Dispense records cannot be deleted.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED
        )



class PharmacyBillItemViewSet(viewsets.ModelViewSet):
    """
    PATCH  /bill-items/<id>/         → update unit_price only
    DELETE /bill-items/<id>/         → soft delete
    """
    serializer_class       = PharmacyBillItemSerializer
    authentication_classes = []
    permission_classes     = [AllowAny]

    def get_queryset(self):
        queryset = PharmacyBillItem.objects.select_related(
            "medicine_dispense__medicine_batch__medicine",
            "billing"
        ).all()

        # filter by billing id
        billing_id = self.request.query_params.get("billing")
        if billing_id:
            queryset = queryset.filter(billing_id=billing_id)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset   = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Pharmacy bill items retrieved successfully."
        )

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data,
            message="Bill item retrieved successfully."
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Pharmacy bill item created successfully.",
                status_code=status.HTTP_201_CREATED
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def update(self, request, *args, **kwargs):
        # always partial — only unit_price is editable
        kwargs["partial"] = True
        instance   = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(
                data=serializer.data,
                message="Bill item updated successfully."
            )
        return error_response(
            message="Validation failed.",
            errors=serializer.errors
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()  # soft delete
        return success_response(
            message="Bill item deleted successfully."
        )