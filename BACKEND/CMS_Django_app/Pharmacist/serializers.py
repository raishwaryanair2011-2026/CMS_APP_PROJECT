from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
# from Doctor.models import MedicinePrescription
from .models import (
    MedicineCategory,Medicine,MedicineBatch,MedicineDispense,PharmacyBillItem,
)

class BaseModelSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        try:
            with transaction.atomic():
                return super().create(validated_data)
        except DjangoValidationError as e:
            if hasattr(e, "message_dict"):
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError({"error": e.messages})
        except IntegrityError:
            raise serializers.ValidationError(
                {"database_error": "A database constraint was violated."}
            )

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except DjangoValidationError as e:
            if hasattr(e, "message_dict"):
                raise serializers.ValidationError(e.message_dict)
            raise serializers.ValidationError({"error": e.messages})
        except IntegrityError:
            raise serializers.ValidationError(
                {"database_error": "A database constraint was violated."}
            )


class MedicineCategorySerializer(BaseModelSerializer):

    class Meta:
        model = MedicineCategory
        fields = ["id", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category name cannot be empty."
            )
        if len(value) < 3:
            raise serializers.ValidationError(
                "Category name must be at least 3 characters."
            )

        # Normalize to title case
        return value.title()


class MedicineSerializer(BaseModelSerializer):

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    #properties from model
    total_stock = serializers.IntegerField(read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Medicine
        fields = [
            "id",
            "name",
            "generic_name",
            "company",
            "price",
            "category",       
            "category_name",   
            "reorder_level",
            "is_active",
            "total_stock",    
            "needs_reorder",   
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_stock",
            "needs_reorder",
            "created_at",
            "updated_at",
        ]


    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Medicine name cannot be empty."
            )
        if len(value) < 2:
            raise serializers.ValidationError(
                "Medicine name must be at least 2 characters."
            )
        return value

    def validate_generic_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Generic name cannot be empty."
            )
        return value

    def validate_company(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Company name cannot be empty."
            )
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Price must be greater than zero."
            )
        return value

    def validate_reorder_level(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Reorder level cannot be negative."
            )
        return value

    #update logic
    def update(self, instance, validated_data):
        instance.name  = validated_data.get("name", instance.name)
        instance.generic_name  = validated_data.get("generic_name",  instance.generic_name)
        instance.company  = validated_data.get("company",   instance.company)
        instance.price = validated_data.get("price",   instance.price)
        instance.category  = validated_data.get("category", instance.category)
        instance.reorder_level = validated_data.get("reorder_level", instance.reorder_level)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.save()
        return instance



class MedicineBatchSerializer(BaseModelSerializer):

    medicine_name  = serializers.CharField(
        source="medicine.name",
        read_only=True
    )
    medicine_generic = serializers.CharField(
        source="medicine.generic_name",
        read_only=True
    )

    #properties from model
    is_expired   = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model  = MedicineBatch
        fields = [
            "id",
            "batch_no",
            "medicine",           # write — FK id
            "medicine_name",      # read  — nested
            "medicine_generic",   # read  — nested
            "stock_level",
            "purchase_date",
            "expiry_date",
            "is_active",
            "is_expired",         # read  — computed
            "is_out_of_stock",    # read  — computed
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_expired",
            "is_out_of_stock",
            "created_at",
            "updated_at",
        ]

    def validate_batch_no(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Batch number cannot be empty."
            )
        return value

    def validate_stock_level(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Stock level cannot be negative."
            )
        return value

    def validate_expiry_date(self, value):
        from django.utils import timezone
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Cannot add a batch that is already expired."
            )
        return value


    #crossfield validation
    def validate(self, data):
        purchase_date = data.get("purchase_date")
        expiry_date   = data.get("expiry_date")

        if purchase_date and expiry_date:
            if expiry_date <= purchase_date:
                raise serializers.ValidationError({
                    "expiry_date": "Expiry date must be after purchase date."
                })

        return data


    def update(self, instance, validated_data):
        # medicine and batchno cannot change after creation
        validated_data.pop("medicine", None)
        validated_data.pop("batch_no",  None)

        instance.stock_level  = validated_data.get("stock_level", instance.stock_level)
        instance.purchase_date = validated_data.get("purchase_date", instance.purchase_date)
        instance.expiry_date = validated_data.get("expiry_date", instance.expiry_date)
        instance.is_active  = validated_data.get("is_active", instance.is_active)
        instance.save()
        return instance



class MedicineDispenseSerializer(BaseModelSerializer):
    """
    Deducts stock from MedicineBatch
    Auto deactivates batch if stock = 0
    Flips MedicinePrescription.is_dispensed = True
    All in one atomic transaction.
    """

    # medicine name, dosage, frequency, quantity etc.
    prescription_detail = MedicinePrescriptionReadSerializer(
        source="medicine_prescription",
        read_only=True
    )

    medicine_name     = serializers.CharField(
        source="medicine_batch.medicine.name",
        read_only=True
    )
    batch_no          = serializers.CharField(
        source="medicine_batch.batch_no",
        read_only=True
    )
    dispensed_by_name = serializers.CharField(
        source="dispensed_by.full_name",
        read_only=True
    )

    class Meta:
        model  = MedicineDispense
        fields = [
            "id",
            "dispense_code",           
            "medicine_prescription",   
            "prescription_detail",     
            "medicine_batch",        
            "medicine_name",         
            "batch_no",              
            "quantity_dispensed",     
            "dispensed_by",           
            "dispensed_by_name",      
            "dispensed_at",            
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "dispense_code",
            "prescription_detail",
            "medicine_name",
            "batch_no",
            "dispensed_by_name",
            "dispensed_at",
            "created_at",
            "updated_at",
        ]


    def validate_quantity_dispensed(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity dispensed must be at least 1."
            )
        return value


    def validate(self, data):
        prescription       = data.get("medicine_prescription")
        batch       = data.get("medicine_batch")
        quantity_dispensed = data.get("quantity_dispensed")

        if prescription.is_dispensed:
            raise serializers.ValidationError(
                "This prescription item has already been dispensed."
            )

        if not batch.is_active:
            raise serializers.ValidationError({
                "medicine_batch": "Inactive batch cannot be used."
            })

        if batch.is_deleted:
            raise serializers.ValidationError({
                "medicine_batch": "This batch has been deleted."
            })

        if batch.is_expired:
            raise serializers.ValidationError({
                "medicine_batch": "Batch is expired."
            })

        if quantity_dispensed > batch.stock_level:
            raise serializers.ValidationError({
                "quantity_dispensed": (
                    f"Insufficient stock. "
                    f"Available: {batch.stock_level}, "
                    f"Requested: {quantity_dispensed}."
                )
            })

        if quantity_dispensed > prescription.quantity:
            raise serializers.ValidationError({
                "quantity_dispensed": (
                    f"Quantity exceeds prescribed amount. "
                    f"Prescribed: {prescription.quantity}, "
                    f"Requested: {quantity_dispensed}."
                )
            })

        if batch.medicine != prescription.medicine:
            raise serializers.ValidationError({
                "medicine_batch": "Batch medicine does not match prescribed medicine."
            })

        return data


    def create(self, validated_data):
    #    for custom save to execute 
        dispense = MedicineDispense(**validated_data)
        dispense.save()  # model save() handles everything
        return dispense


    def update(self, instance, validated_data):
        raise serializers.ValidationError(
            "Dispense records cannot be updated once created."
        )


class PharmacyBillItemSerializer(BaseModelSerializer):
    """
    On create():
    - Auto snapshots unit_price from Medicine.price if not provided
    - Auto calculates total_price = unit_price × quantity_dispensed

    On update():
    - Only unit_price can be updated
    - total_price always recalculated
    - billing and medicine_dispense links are locked
    """

    medicine_name   = serializers.CharField(
        source="medicine_dispense.medicine_batch.medicine.name",
        read_only=True
    )
    batch_no  = serializers.CharField(
        source="medicine_dispense.medicine_batch.batch_no",
        read_only=True
    )
    quantity_dispensed = serializers.IntegerField(
        source="medicine_dispense.quantity_dispensed",
        read_only=True
    )

    class Meta:
        model  = PharmacyBillItem
        fields = [
            "id",
            "billing",             
            "medicine_dispense",    
            "medicine_name",      
            "batch_no",             
            "quantity_dispensed",   
            "unit_price",           
            "total_price",          # auto calculated
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_price",
            "medicine_name",
            "batch_no",
            "quantity_dispensed",
            "created_at",
            "updated_at",
        ]


    def validate_unit_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError(
                "Unit price must be greater than zero."
            )
        return value


    def validate(self, data):
        medicine_dispense = data.get("medicine_dispense")

        # Check duplicate bill item for same dispense
        if PharmacyBillItem.objects.filter(
            medicine_dispense=medicine_dispense
        ).exists():
            raise serializers.ValidationError(
                "A bill item already exists for this dispense record."
            )

        return data


    #custom create
    def create(self, validated_data):
        dispense = validated_data.get("medicine_dispense")

        # auto snapshot price from Medicine if not provided
        if not validated_data.get("unit_price"):
            validated_data["unit_price"] = (
                dispense.medicine_batch.medicine.price
            )

        #auto calculate total price
        validated_data["total_price"] = (
            validated_data["unit_price"] * dispense.quantity_dispensed
        )

        return PharmacyBillItem.objects.create(**validated_data)


    #only unitprice editable
    def update(self, instance, validated_data):
        # connected relationship fields
        validated_data.pop("medicine_dispense", None)
        validated_data.pop("billing",  None)

        unit_price = validated_data.get("unit_price", instance.unit_price)

        if unit_price <= 0:
            raise serializers.ValidationError({
                "unit_price": "Unit price must be greater than zero."
            })

        instance.unit_price  = unit_price
        # Always recalculate total on price update
        instance.total_price = (
            unit_price * instance.medicine_dispense.quantity_dispensed
        )
        instance.save()
        return instance