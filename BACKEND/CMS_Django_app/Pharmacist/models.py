from django.db import models

# Create your models here.


from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class MedicineCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Medicine(models.Model):
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        MedicineCategory,
        on_delete=models.PROTECT,
        related_name="medicines"
    )
    reorder_level = models.PositiveIntegerField(
        default=10,
        help_text="Minimum stock level before reorder is needed"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.generic_name})"

    def clean(self):
        if self.price <= 0:
            raise ValidationError({"price": "Price must be greater than 0."})

        if self.reorder_level < 0:
            raise ValidationError({"reorder_level": "Reorder level cannot be negative."})

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


class MedicineBatch(models.Model):
    batch_no = models.CharField(max_length=100)
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="batches"
    )
    stock_level = models.PositiveIntegerField(default=0)
    purchase_date = models.DateField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["expiry_date"] 
        unique_together = ("medicine", "batch_no")

    def __str__(self):
        return f"{self.medicine.name} | Batch: {self.batch_no} | Stock: {self.stock_level}"

    def clean(self):
        if self.expiry_date and self.purchase_date:
            if self.expiry_date <= self.purchase_date:
                raise ValidationError({
                    "expiry_date": "Expiry date must be after purchase date."
                })

        if self.expiry_date and self.expiry_date < timezone.now().date():
            raise ValidationError({
                "expiry_date": "Cannot add a batch that is already expired."
            })

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def is_out_of_stock(self):
        return self.stock_level == 0


class MedicineDispense(models.Model):
    medicine_prescription = models.OneToOneField(
        "doctor.MedicinePrescription",
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
        return (
            f"Dispense #{self.id} | "
            f"{self.medicine_batch.medicine.name} | "
            f"Qty: {self.quantity_dispensed}"
        )

    def clean(self):
        if self.medicine_prescription.is_dispensed:
            raise ValidationError(
                "This prescription item has already been dispensed."
            )

        if not self.medicine_batch.is_active:
            raise ValidationError({
                "medicine_batch": "This batch is inactive and cannot be used."
            })

        if self.medicine_batch.is_expired:
            raise ValidationError({
                "medicine_batch": "This batch has expired and cannot be dispensed."
            })

        if self.quantity_dispensed > self.medicine_batch.stock_level:
            raise ValidationError({
                "quantity_dispensed": (
                    f"Insufficient stock. "
                    f"Available: {self.medicine_batch.stock_level}, "
                    f"Requested: {self.quantity_dispensed}."
                )
            })

        if self.quantity_dispensed > self.medicine_prescription.quantity:
            raise ValidationError({
                "quantity_dispensed": (
                    f"Quantity exceeds prescribed amount. "
                    f"Prescribed: {self.medicine_prescription.quantity}, "
                    f"Requested: {self.quantity_dispensed}."
                )
            })

        if self.medicine_batch.medicine != self.medicine_prescription.medicine:
            raise ValidationError({
                "medicine_batch": (
                    "Batch medicine does not match the prescribed medicine."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        self.medicine_batch.stock_level -= self.quantity_dispensed
        self.medicine_batch.save()

        if self.medicine_batch.stock_level == 0:
            self.medicine_batch.is_active = False
            self.medicine_batch.save()

        self.medicine_prescription.is_dispensed = True
        self.medicine_prescription.save()



class PharmacyBillItem(models.Model):
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
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price snapshot from Medicine.price at billing time"
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return (
            f"BillItem #{self.id} | "
            f"{self.medicine_dispense.medicine_batch.medicine.name} | "
            f"Total: {self.total_price}"
        )

    def clean(self):
        if self.unit_price <= 0:
            raise ValidationError({"unit_price": "Unit price must be greater than 0."})

        if self.total_price <= 0:
            raise ValidationError({"total_price": "Total price must be greater than 0."})

    def save(self, *args, **kwargs):
        # Auto snapshot price from Medicine if not set
        if not self.unit_price:
            self.unit_price = (
                self.medicine_dispense.medicine_batch.medicine.price
            )

        # Auto calculate total price
        self.total_price = (
            self.unit_price * self.medicine_dispense.quantity_dispensed
        )

        self.full_clean()
        super().save(*args, **kwargs)
