from apps.payments.models import Order, OrderStatus

def unverified_orders_count(request):
    """
    Context processor to provide the count of orders waiting for verification
    to all templates, useful for sidebar notification dots.
    """
    if request.user.is_authenticated and getattr(request.user, 'role', '') in ['admin', 'staff']:
        count = Order.objects.filter(status=OrderStatus.WAITING_VERIFICATION).count()
        return {'unverified_orders_count': count}
    return {}
