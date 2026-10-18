from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


def user_can_access_surface(user: AuthenticatedUser, surface: str) -> bool:
    return surface in user.allowed_surfaces and surface == user.authorization_surface
