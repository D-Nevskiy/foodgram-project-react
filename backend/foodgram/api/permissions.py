from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated or request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        return obj.author == request.user or request.method in SAFE_METHODS


class IsAuthenticatedOrReadOnlyListRetrieve(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if view.action in ['list', 'retrieve']:
            return True
        return request.user.is_authenticated
