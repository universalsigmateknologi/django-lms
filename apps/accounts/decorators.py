from django.shortcuts import redirect

def role_required(allowed_roles=[], redirect_url='login'):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(redirect_url)

            if request.user.role not in allowed_roles:
                return redirect('no_permission')  # buat halaman khusus

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator