export const ADMIN_ROLE = 'admin';

export function isAdminUser(user) {
  if (!user) return false;
  return user.role === ADMIN_ROLE
    || user.permissions?.some((permission) => ['users:write', 'users:manage'].includes(permission));
}
