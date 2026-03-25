from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MedicineCategoryViewSet,
    MedicineViewSet,
    MedicineBatchViewSet,
    PrescriptionViewSet,
    MedicineDispenseViewSet,
    PharmacyBillItemViewSet,
    PharmacistDashboardView,
)

# router handles all ViewSets
router = DefaultRouter()
router.register(r'categories', MedicineCategoryViewSet,  basename='category')
router.register(r'medicines',  MedicineViewSet,   basename='medicine')
router.register(r'batches',  MedicineBatchViewSet, basename='batch')
router.register(r'prescriptions',PrescriptionViewSet, basename='prescription')
router.register(r'dispense',  MedicineDispenseViewSet, basename='dispense')
router.register(r'bill-items',  PharmacyBillItemViewSet, basename='bill-item')


urlpatterns = [


    #  Medicine 

    # GET    /medicines/needs_reorder=true  - filter low stock
    # DELETE /medicines/id/                - soft delete

    #  Medicine Batch 

    # GET    /batches/?expiring_soon=true   - expiring within 30 days
    # PUT    /batches/id/                 - update (medicine+batch_no locked)


    #  Prescriptions (Read Only) 
    # GET    /prescriptions/pending/   - pending prescriptions only
    # GET    /prescriptions/id/      - single prescription detail

    #  Medicine Dispense 
    # POST   /dispense/         - dispense medicine
    #                             triggers:
    #                             1. creates dispense record
    #                             2. generates dispense_code
    #                             3. deducts stock from batch
    #                             4. auto deactivates batch if stock = 0
    #                             5. flips is_dispensed = True
    # PUT    /dispense/<id>/    - DISABLED — immutable
    # DELETE /dispense/<id>/    - DISABLED — immutable

    #  Pharmacy Bill Items 
    # POST   /bill-items/               - create bill item
    #                                     auto fills unit_price
    #                                     auto calculates total_price
    # PATCH  /bill-items/id/           - update unit_price only

    *router.urls,
    path(
        'dashboard/',
        PharmacistDashboardView.as_view(),
        name='pharmacist-dashboard'
    ),
]