from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrReadOnlyWithAdminPass(BasePermission):
    """
    ✅ 공통 권한 규칙
    - SAFE_METHODS(GET/HEAD/OPTIONS): 누구나 허용
    - superuser: 무조건 허용
    - 그 외: obj.user == request.user 일 때만 허용
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.user and request.user.is_superuser:
            return True
        owner = getattr(obj, "user", None)
        return owner == request.user
