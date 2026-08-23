from django.core.exceptions import ValidationError
from apps.users.models import Role
from core.permissions_registry import get_all_permission_codes

class RoleService:
    @staticmethod
    def create_role(tenant, name: str, description: str = '', permissions: list = None, is_system: bool = False) -> Role:
        permissions = permissions or []
        all_codes = get_all_permission_codes()
        invalid_codes = [p for p in permissions if p not in all_codes]
        if invalid_codes:
            raise ValidationError(f"Invalid permission code(s): {', '.join(invalid_codes)}")

        role = Role.objects.create(
            tenant=tenant,
            name=name.strip(),
            description=description.strip(),
            permissions=permissions,
            is_system=is_system
        )
        return role

    @staticmethod
    def update_role(role: Role, name: str = None, description: str = None, permissions: list = None) -> Role:
        if role.is_system and name and name != role.name:
            raise ValidationError("Cannot rename system roles.")

        if permissions is not None:
            all_codes = get_all_permission_codes()
            invalid_codes = [p for p in permissions if p not in all_codes]
            if invalid_codes:
                raise ValidationError(f"Invalid permission code(s): {', '.join(invalid_codes)}")
            role.permissions = permissions

        if name is not None:
            role.name = name.strip()
        if description is not None:
            role.description = description.strip()

        role.save()
        return role

    @staticmethod
    def delete_role(role: Role) -> None:
        if role.is_system:
            raise ValidationError("Cannot delete built-in system roles.")
        if role.users.exists():
            raise ValidationError(f"Cannot delete role '{role.name}' as it is currently assigned to {role.users.count()} user(s).")
        role.delete()
