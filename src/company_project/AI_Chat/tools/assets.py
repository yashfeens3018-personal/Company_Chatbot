from datetime import datetime

from langchain.tools import tool

from ...queries.assets import (
    get_asset,
    get_asset_stats,
    get_employee_assets,
    get_expiring_warranties,
    get_unassigned_assets,
    search_assets,
)


@tool
def get_asset_tool(
    asset_id: int | None = None,
    asset_tag: str | None = None,
    serial_number: str | None = None,
):
    """Fetch ONE specific asset using its asset ID, asset tag, or serial number.

    Use this only when the user gives an exact identifier for a single asset
    (e.g. "asset 12", "tag LAP-0042", "serial number SN12345"). To find assets
    by brand, type, status, condition, owner, or dates, use
    ``search_assets_tool`` instead.

    Provide exactly ONE of the three identifiers, never more than one and
    never none. Matching is exact. Never guess an identifier.

    Returns a list with one row: asset_id, asset_tag, asset_type, brand,
    model, serial_number, purchase_date, purchase_cost, status, assigned_to
    (employee ID of the holder, or None if unassigned), condition,
    warranty_expiry, created_at. An identifier that does not exist raises a
    not-found error.

    Args:
        asset_id: Numeric asset ID (integer greater than 0).
        asset_tag: Exact asset tag text, e.g. "LAP-0042".
        serial_number: Exact manufacturer serial number text.
    """
    return get_asset(asset_id, asset_tag, serial_number)


@tool
def search_assets_tool(
    asset_type: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    status: str | None = None,
    condition: str | None = None,
    assigned_to_first_name: str | None = None,
    assigned_to_last_name: str | None = None,
    purchase_cost_min: float | None = None,
    purchase_cost_max: float | None = None,
    purchase_from: datetime | None = None,
    purchase_to: datetime | None = None,
    warranty_from: datetime | None = None,
    warranty_to: datetime | None = None,
):
    """List or search assets by type, brand, model, status, condition, owner, cost, or dates.

    This is the default tool for any asset request that does not give an
    asset ID, tag, or serial number. All filters are optional and combined
    with AND. With NO arguments it returns ALL assets. Always returns a
    list, even for one match.

    Do NOT use this for counts, totals, or average cost (use
    ``get_asset_stats_tool``), for assets nobody holds (use
    ``get_unassigned_assets_tool``), or for warranties expiring soon (use
    ``get_expiring_warranties_tool``).

    Each row contains: asset_id, asset_tag, asset_type, brand, model,
    serial_number, purchase_date, purchase_cost, status, assigned_to
    (employee ID, or None if unassigned), condition, warranty_expiry.

    Args:
        asset_type: Kind of asset, free text such as "laptop" or "phone".
            Case-insensitive partial match.
        brand: Manufacturer, e.g. "Dell". Case-insensitive partial match.
        model: Model name, e.g. "XPS". Case-insensitive partial match.
        status: Must be exactly one of: "available", "assigned",
            "in_repair", "lost", "disposed" (lowercase, underscore in
            "in_repair"). Any other value causes an error.
        condition: Must be exactly one of: "excellent", "good", "fair",
            "poor", "damaged" (lowercase). Any other value causes an error.
        assigned_to_first_name: First name of the employee holding the asset.
            Provide this together with ``assigned_to_last_name``.
        assigned_to_last_name: Last name of the employee holding the asset.
            Matching is case-insensitive and exact; assets held by employees
            with matching full names are included.
        purchase_cost_min: Minimum purchase cost, inclusive.
        purchase_cost_max: Maximum purchase cost, inclusive.
        purchase_from: Only assets purchased on or after this date (ISO 8601,
            e.g. "2024-01-31T00:00:00").
        purchase_to: Only assets purchased on or before this date.
        warranty_from: Only assets whose warranty expires on or after this
            date.
        warranty_to: Only assets whose warranty expires on or before this
            date.
    """
    return search_assets(
        asset_type=asset_type,
        brand=brand,
        model=model,
        status=status,
        condition=condition,
        assigned_to_first_name=assigned_to_first_name,
        assigned_to_last_name=assigned_to_last_name,
        purchase_cost_min=purchase_cost_min,
        purchase_cost_max=purchase_cost_max,
        purchase_from=purchase_from,
        purchase_to=purchase_to,
        warranty_from=warranty_from,
        warranty_to=warranty_to,
    )


@tool
def get_asset_stats_tool(
    asset_type: str | None = None,
    status: str | None = None,
    condition: str | None = None,
):
    """Count assets and compute their total and average purchase cost.

    Use this for "how many assets", "how many laptops are in repair", "total
    value of our assets", or "average cost of phones". It returns numbers
    only, NOT the list of assets; to see the actual assets, use
    ``search_assets_tool``.

    Filters are optional and combined with AND. With NO arguments it covers
    the entire asset inventory.

    Returns a list with one row: "Total Assets" (count), "Total Purchase
    Cost" (sum), "Average Purchase Cost". Cost values are None when no assets
    match.

    Args:
        asset_type: Exact asset type text, e.g. "Laptop". Matching is
            exact and case-sensitive here, so use the type as stored.
        status: One of: "available", "assigned", "in_repair", "lost",
            "disposed" (lowercase, underscore in "in_repair").
        condition: One of: "excellent", "good", "fair", "poor", "damaged"
            (lowercase).
    """
    return get_asset_stats(asset_type, status, condition)


@tool
def get_employee_assets_tool(first_name: str, last_name: str):
    """List assets currently assigned to employees with the given full name.

    Use for "what assets does Alex Smith have". The query looks up the
    employee ID using the exact first and last name, ignoring case. If
    multiple employees share that name, assets for all of them are returned.
    If no employee matches, a not-found error is raised.

    Each row contains: asset_id, asset_tag, asset_type, brand, model,
    serial_number, status, condition, purchase_date, warranty_expiry.

    Args:
        first_name: Employee's exact first name.
        last_name: Employee's exact last name.
    """
    return get_employee_assets(first_name, last_name)


@tool
def get_unassigned_assets_tool(
    asset_type: str | None = None,
    status: str | None = None,
    condition: str | None = None,
):
    """List assets that are not assigned to any employee.

    Use for "which assets are free", "unassigned laptops", or "spare
    equipment". Only assets with no holder are returned. With NO arguments
    it returns all unassigned assets. Filters are optional and combined with
    AND. For counts only, use ``get_asset_stats_tool``.

    Each row contains: asset_id, asset_tag, asset_type, brand, model,
    serial_number, status, condition, purchase_date, warranty_expiry.

    Args:
        asset_type: Exact asset type text, e.g. "Laptop". Matching is
            exact and case-sensitive here, so use the type as stored.
        status: One of: "available", "assigned", "in_repair", "lost",
            "disposed" (lowercase, underscore in "in_repair"). Any other
            value causes an error.
        condition: One of: "excellent", "good", "fair", "poor", "damaged"
            (lowercase). Any other value causes an error.
    """
    return get_unassigned_assets(asset_type, status, condition)


@tool
def get_expiring_warranties_tool(
    expiry_from: datetime | None = None,
    expiry_to: datetime | None = None,
):
    """List assets whose warranty expires within a date range, soonest first.

    Use for "warranties expiring this month", "which warranties end before
    2027", or "warranty expiry between June and August". Only assets that
    have a warranty date are included. Results are sorted by warranty expiry,
    earliest first. With NO dates it returns every asset that has a
    warranty date, including ones already expired.

    Each row contains: asset_id, asset_tag, asset_type, brand, model,
    assigned_to (employee ID, or None), warranty_expiry.

    Args:
        expiry_from: Only warranties expiring on or after this date
            (ISO 8601, e.g. "2026-11-01T00:00:00").
        expiry_to: Only warranties expiring on or before this date.
            Must not be earlier than ``expiry_from`` when both are given.
    """
    return get_expiring_warranties(expiry_from, expiry_to)