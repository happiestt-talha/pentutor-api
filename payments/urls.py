from django.urls import path
from .views import (
    initiate_jazzcash, verify_jazzcash,
    initiate_easypaisa, verify_easypaisa,
)

urlpatterns = [
    path('jazzcash/initiate/', initiate_jazzcash),
    path('jazzcash/verify/', verify_jazzcash),
    path('easypaisa/initiate/', initiate_easypaisa),
    path('easypaisa/verify/', verify_easypaisa),
]
