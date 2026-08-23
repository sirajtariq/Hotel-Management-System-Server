from django.db.models import Count
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from core.viewsets import TenantScopedViewSet
from apps.users.models import User, Role
from apps.users.serializers import (
    UserSerializer,
    UserCreateSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    AdminResetPasswordSerializer,
    RoleSerializer,
)
from apps.users.services.user_service import UserService
from apps.users.services.role_service import RoleService
from core.permissions import IsTenantAdmin, HasTenantAccess, HasModulePermission
from core.permissions_registry import PERMISSIONS_CATALOG

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(TenantScopedViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related('custom_role', 'tenant')

    def get_serializer_class(self):

        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ['create']:
            # Anyone can register or TenantAdmin creates user
            return [permissions.AllowAny()]
        if self.action in ['me', 'change_password']:
            return [permissions.IsAuthenticated()]
        return [IsTenantAdmin()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_data = serializer.validated_data
        tenant_id = user_data.get('tenant').id if user_data.get('tenant') else None
        
        # Non-superadmins automatically scope to their tenant
        if not request.user.is_superuser and getattr(request.user, 'role', '') != 'SUPERADMIN':
            if getattr(request.user, 'tenant_id', None):
                tenant_id = request.user.tenant_id

        user = UserService.create_user(
            username=user_data['username'],
            email=user_data.get('email', ''),
            password=user_data['password'],
            role=user_data.get('role', 'GUEST'),
            tenant_id=tenant_id,
            first_name=user_data.get('first_name', ''),
            last_name=user_data.get('last_name', ''),
            phone_number=user_data.get('phone_number', '')
        )

        tokens = UserService.generate_tokens_for_user(user)
        response_data = UserSerializer(user).data
        response_data['tokens'] = tokens

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        if request.method == 'GET':
            user = User.objects.select_related('tenant', 'custom_role').get(id=request.user.id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)

        serializer.is_valid(raise_exception=True)

        updated_user = UserService.update_user_profile(user, serializer.validated_data)
        return Response(UserSerializer(updated_user).data)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """
        Allows any logged-in user to change their OWN password via UserService.
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserService.change_user_password(
            user=request.user,
            old_password=serializer.validated_data['old_password'],
            new_password=serializer.validated_data['new_password']
        )

        return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def reset_password(self, request, pk=None):
        """
        Allows SuperAdmin or TenantAdmin to reset ANOTHER user's password via UserService.
        """
        target_user = self.get_object()
        serializer = AdminResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        UserService.admin_reset_user_password(
            request_user=request.user,
            target_user=target_user,
            new_password=serializer.validated_data['new_password']
        )

        return Response(
            {'detail': f'Password for user "{target_user.username}" reset successfully.'},
            status=status.HTTP_200_OK
        )


class RoleViewSet(TenantScopedViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, HasTenantAccess, HasModulePermission]
    action_permissions = {
        'list': 'roles:manage',
        'retrieve': 'roles:manage',
        'create': 'roles:manage',
        'update': 'roles:manage',
        'partial_update': 'roles:manage',
        'destroy': 'roles:manage',
        'available_permissions': 'roles:manage',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.annotate(users_count=Count('users', distinct=True))

    @action(detail=False, methods=['get'])
    def available_permissions(self, request):
        """
        Returns PERMISSIONS_CATALOG directly from core/permissions_registry.py.
        """
        return Response(PERMISSIONS_CATALOG, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tenant = request.user.tenant
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'SUPERADMIN':
            tenant = serializer.validated_data.get('tenant', tenant)

        role = RoleService.create_role(
            tenant=tenant,
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            permissions=serializer.validated_data.get('permissions', []),
            is_system=serializer.validated_data.get('is_system', False)
        )
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        updated_role = RoleService.update_role(
            role=instance,
            name=serializer.validated_data.get('name'),
            description=serializer.validated_data.get('description'),
            permissions=serializer.validated_data.get('permissions')
        )
        return Response(RoleSerializer(updated_role).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        RoleService.delete_role(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)



