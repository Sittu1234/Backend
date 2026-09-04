from django.db.models import Q


def is_company_viewer(user):
    return bool(user and (user.is_admin or user.is_accountant))


def dealer_queryset(qs, user):
    if is_company_viewer(user):
        return qs
    if user.is_sales:
        return qs.filter(party_type="dealer").filter(Q(assigned_to=user) | Q(created_by=user))
    return qs.none()


def invoice_queryset(qs, user):
    if is_company_viewer(user):
        return qs
    if user.is_sales:
        return qs.filter(Q(created_by=user) | Q(customer__assigned_to=user))
    return qs.none()
