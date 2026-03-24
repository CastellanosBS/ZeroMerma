from __future__ import annotations

from fastapi import FastAPI

from zeromerma_api.main import create_app


def _paths(app: FastAPI) -> dict:
    """
    Return the OpenAPI path map for the current app instance.
    """
    return app.openapi()["paths"]


def _assert_path_has_method(paths: dict, path: str, method: str) -> None:
    """
    Assert that one OpenAPI path exposes one HTTP method.
    """
    assert path in paths, f"Missing path: {path}"
    assert method in paths[path], f"Missing method {method.upper()} for path: {path}"


def test_pos_v1_official_route_surface_exists() -> None:
    """
    Freeze the official POS v1 route surface.

    This is a contract-surface test, not a behavior test.
    Its job is to make route drift visible immediately.
    """
    app = create_app()
    paths = _paths(app)

    official_routes = [
        ("get", "/pos/bootstrap"),
        ("post", "/pos/checkout"),
        ("post", "/pos/stock/finished-goods"),
        ("post", "/pos/sales/{sale_id}/reprint"),
        ("post", "/pos/cash-sessions/open"),
        ("post", "/pos/cash-sessions/{session_id}/close"),
        ("get", "/pos/cash-sessions/current"),
        ("post", "/pos/sales"),
        ("get", "/pos/sales"),
        ("get", "/pos/sales/{sale_id}"),
        ("post", "/pos/sales/{sale_id}/payments"),
        ("post", "/pos/sales/{sale_id}/void"),
        ("post", "/pos/sales/{sale_id}/refund"),
        ("post", "/pos/orders"),
        ("get", "/pos/orders"),
        ("get", "/pos/orders/{order_id}"),
        ("get", "/pos/orders/queue"),
        ("post", "/pos/orders/{order_id}/send-to-bakery"),
        ("post", "/pos/orders/{order_id}/ready"),
        ("get", "/pos/orders/{order_id}/checkout-preview"),
        ("post", "/pos/orders/{order_id}/deliver-checkout"),
        ("post", "/pos/orders/{order_id}/deliver"),
        ("post", "/pos/orders/{order_id}/cancel"),
        ("get", "/pos/audit-events"),
    ]

    for method, path in official_routes:
        _assert_path_has_method(paths, path, method)


def test_pos_v1_exceptional_manual_delivery_route_is_still_exposed() -> None:
    """
    Keep visibility over the exceptional manual-delivery route.

    This route is intentionally still present in v1, but it is not the
    normative commercial closure path.
    """
    app = create_app()
    paths = _paths(app)

    _assert_path_has_method(paths, "/pos/orders/{order_id}/deliver", "post")
    _assert_path_has_method(paths, "/pos/orders/{order_id}/deliver-checkout", "post")


def test_pos_v1_reversal_routes_exist() -> None:
    """
    Freeze the existence of the official sale-reversal routes.
    """
    app = create_app()
    paths = _paths(app)

    _assert_path_has_method(paths, "/pos/sales/{sale_id}/void", "post")
    _assert_path_has_method(paths, "/pos/sales/{sale_id}/refund", "post")


def test_pos_v1_audit_route_exists() -> None:
    """
    Freeze the existence of the persisted audit-trail read route.
    """
    app = create_app()
    paths = _paths(app)

    _assert_path_has_method(paths, "/pos/audit-events", "get")
