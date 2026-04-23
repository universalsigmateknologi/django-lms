from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, authenticate, login
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .tokens import email_verification_token

User = get_user_model()

# Create your views here.
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            if not user.is_verified:
                messages.error(request, 'Email belum diverifikasi!')
                return redirect('login')

            login(request, user)
            return redirect('dashboard')

    return render(request, 'accounts/login.html')

def register(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Password tidak sama!')
            return redirect('register')

        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            is_active=False
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)

        verification_link = request.build_absolute_uri(
            reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
        )

        send_mail(
            'Verify your email',
            f'Klik link ini untuk verifikasi:\n{verification_link}',
            None,
            [email],
        )

        messages.success(request, 'Cek email untuk verifikasi!')
        return redirect('login')

    return render(request, 'accounts/register.html')

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except:
        user = None

    if user and email_verification_token.check_token(user, token):
        user.is_active = True
        user.is_verified = True
        user.save()

        messages.success(request, 'Email berhasil diverifikasi!')
        return redirect('login')
    else:
        messages.error(request, 'Link tidak valid atau expired!')
        return redirect('register')