"""
Forms for the payments app.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import ManualPaymentProof


class PaymentProofForm(forms.ModelForm):
    """
    Form untuk upload bukti pembayaran manual.
    """

    class Meta:
        model  = ManualPaymentProof
        fields = ["proof_image", "sender_name", "sender_bank", "notes"]
        widgets = {
            "proof_image": forms.ClearableFileInput(
                attrs={
                    "accept": "image/jpeg,image/png,image/webp",
                    "class": "hidden",
                    "id": "proof-image-input",
                }
            ),
            "sender_name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full px-4 py-3 bg-white border border-slate-200 "
                        "rounded-xl text-sm text-slate-800 placeholder-slate-400 "
                        "focus:outline-none focus:ring-2 focus:ring-indigo-500/30 "
                        "focus:border-indigo-400 transition-all"
                    ),
                    "placeholder": "Nama sesuai rekening pengirim",
                    "id": "sender-name-input",
                }
            ),
            "sender_bank": forms.TextInput(
                attrs={
                    "class": (
                        "w-full px-4 py-3 bg-white border border-slate-200 "
                        "rounded-xl text-sm text-slate-800 placeholder-slate-400 "
                        "focus:outline-none focus:ring-2 focus:ring-indigo-500/30 "
                        "focus:border-indigo-400 transition-all"
                    ),
                    "placeholder": "Contoh: BCA, BNI, GoPay",
                    "id": "sender-bank-input",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": (
                        "w-full px-4 py-3 bg-white border border-slate-200 "
                        "rounded-xl text-sm text-slate-800 placeholder-slate-400 "
                        "focus:outline-none focus:ring-2 focus:ring-indigo-500/30 "
                        "focus:border-indigo-400 transition-all resize-none"
                    ),
                    "placeholder": "Catatan tambahan (opsional)",
                    "rows": 3,
                    "id": "notes-input",
                }
            ),
        }
        labels = {
            "proof_image": _("Bukti Transfer"),
            "sender_name": _("Nama Pengirim"),
            "sender_bank": _("Bank Pengirim"),
            "notes": _("Catatan"),
        }

    def clean_proof_image(self):
        image = self.cleaned_data.get("proof_image")
        if image:
            # Validate file size (max 5MB)
            max_size = 5 * 1024 * 1024  # 5MB
            if image.size > max_size:
                raise ValidationError(
                    _("Ukuran file terlalu besar. Maksimal 5MB."),
                    code="file_too_large",
                )

            # Validate content type
            allowed_types = ["image/jpeg", "image/png", "image/webp"]
            if hasattr(image, "content_type") and image.content_type not in allowed_types:
                raise ValidationError(
                    _("Format file tidak didukung. Gunakan JPG, PNG, atau WebP."),
                    code="invalid_type",
                )
        return image
