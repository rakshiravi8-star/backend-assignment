from rest_framework.permissions import BasePermission


class IsFacilitator(BasePermission):
    def has_permission(self, request, view):
        return getattr(getattr(request.user, 'profile', None), 'role', None) == 'FACILITATOR'


class IsSeeker(BasePermission):
    def has_permission(self, request, view):
        return getattr(getattr(request.user, 'profile', None), 'role', None) == 'SEEKER'