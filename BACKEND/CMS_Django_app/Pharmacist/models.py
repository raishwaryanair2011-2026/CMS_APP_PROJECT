
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class TimeStampedSoftDeleteModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    objects = ActiveManager()  

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()



class MedicineCategory(TimeStampedSoftDeleteModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name



class Medicine(TimeStampedSoftDeleteModel):

    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    category = models.ForeignKey(
        MedicineCategory,
        on_delete=models.PROTECT,
        related_name="medicines"
    )

    reorder_level = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["name", "generic_name", "company"],
                name="unique_medicine_definition"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.generic_name})"

    def clean(self):

        errors = {}

        if self.price <= 0:
            errors["price"] = "Price must be greater than zero."
        if self.reorder_level < 0:
            errors["reorder_level"] = "Reorder level cannot be negative."
        if errors:
            raise ValidationError(errors)

    @property
    def total_stock(self):

        return self.batches.filter(
            is_active=True
        ).aggregate(
            total=models.Sum("stock_level")
        )["total"] or 0

    @property
    def needs_reorder(self):
        return self.total_stock <= self.reorder_level



class MedicineBatch(TimeStampedSoftDeleteModel):

    batch_no = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]+$',
                message="Batch number must contain only uppercase letters, numbers, or hyphen."
            )
        ]
    )

    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="batches"
    )

    stock_level = models.PositiveIntegerField(default=0)
    purchase_date = models.DateField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:

        ordering = ["expiry_date"]

        constraints = [
            models.UniqueConstraint(
                fields=["medicine", "batch_no"],
                name="unique_batch_per_medicine"
            )
        ]

    def __str__(self):
        return f"{self.medicine.name} | Batch {self.batch_no}"
    def clean(self):

        errors = {}

        if self.expiry_date and self.purchase_date:
            if self.expiry_date <= self.purchase_date:
                errors["expiry_date"] = "Expiry date must be after purchase date."
        if self.expiry_date and self.expiry_date < timezone.now().date():
            errors["expiry_date"] = "Cannot create a batch that is already expired."
        if errors:
            raise ValidationError(errors)
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def is_out_of_stock(self):
        return self.stock_level == 0



class MedicineDispense(TimeStampedSoftDeleteModel):

    dispense_code = models.CharField(
        max_length=20,
        unique=True,
        editable=False
    )

    medicine_prescription = models.OneToOneField(
        "Doctor.MedicinePrescription",
        on_delete=models.PROTECT,
        related_name="dispense"
    )

    medicine_batch = models.ForeignKey(
        MedicineBatch,
        on_delete=models.PROTECT,
        related_name="dispenses"
    )

    quantity_dispensed = models.PositiveIntegerField()

    dispensed_by = models.ForeignKey(
        "staff.Staff",
        on_delete=models.PROTECT,
        related_name="dispensed_medicines"
    )

    dispensed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dispensed_at"]

    def __str__(self):
        return f"{self.dispense_code}"    
    
    def generate_code(self):
        from django.db.models import Max
        max_id = MedicineDispense.objects.select_for_update().aggregate(
            Max("id")
        )["id__max"] or 0
        return f"DSP{(max_id + 1):05d}"

    def clean(self):

        errors = {}

        if self.medicine_prescription.is_dispensed:
            errors["medicine_prescription"] = "Medicine already dispensed."
        if not self.medicine_batch.is_active:
            errors["medicine_batch"] = "Inactive batch cannot be used."
        if self.medicine_batch.is_deleted:
            errors["medicine_batch"] = "This batch has been deleted."
        if self.medicine_batch.is_expired:
            errors["medicine_batch"] = "Batch is expired."
        if self.quantity_dispensed > self.medicine_batch.stock_level:
            errors["quantity_dispensed"] = "Insufficient stock."
        if self.quantity_dispensed > self.medicine_prescription.quantity:
            errors["quantity_dispensed"] = "Dispense exceeds prescribed quantity."
        if self.medicine_batch.medicine != self.medicine_prescription.medicine:
            errors["medicine_batch"] = "Batch medicine mismatch."
        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):

        with transaction.atomic():

            self.full_clean()
            # generate code INSIDE transaction so select_for_update lock works
            if not self.dispense_code:
                self.dispense_code = self.generate_code()

            super().save(*args, **kwargs)

            self.medicine_batch.stock_level -= self.quantity_dispensed
            self.medicine_batch.save()

            if self.medicine_batch.stock_level == 0:
                self.medicine_batch.is_active = False
                self.medicine_batch.save()

            self.medicine_prescription.is_dispensed = True
            self.medicine_prescription.save()



class PharmacyBillItem(TimeStampedSoftDeleteModel):

    billing = models.ForeignKey(
        "billing.Billing",
        on_delete=models.PROTECT,
        related_name="pharmacy_items"
    )

    medicine_dispense = models.OneToOneField(
        MedicineDispense,
        on_delete=models.PROTECT,
        related_name="bill_item"
    )

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"BillItem {self.id}"
    
    def clean(self):
        errors = {}

        if self.unit_price is not None and self.unit_price <= 0:
            errors["unit_price"] = "Unit price must be greater than zero."
        if self.total_price is not None and self.total_price <= 0:
            errors["total_price"] = "Total price must be greater than zero."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        if not self.unit_price:

            self.unit_price = (
                self.medicine_dispense.medicine_batch.medicine.price
            )
        self.total_price = (
                self.unit_price *
                self.medicine_dispense.quantity_dispensed
        )

        self.full_clean()

        super().save(*args, **kwargs)
