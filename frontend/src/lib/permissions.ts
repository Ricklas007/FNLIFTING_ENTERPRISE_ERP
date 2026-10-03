export function hasPermission(permissions: string[], permission: string) {
  return permissions.includes('*') || permissions.includes(permission)
}
