class CatalogError(Exception):
    """Base catalog error."""


class ProductClassNotFoundError(CatalogError):
    """Raised when a product class is not available for POS usage."""


class ProductNotFoundError(CatalogError):
    """Raised when a product is not available for POS usage."""


class ProductSelectionNotAllowedError(CatalogError):
    """Raised when products are requested for a class that does not support them."""

