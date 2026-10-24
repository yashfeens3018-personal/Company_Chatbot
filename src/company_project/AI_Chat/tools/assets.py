from langchain.tools import tool
from ...queries.assets import get_asset, get_asset_stats, get_employee_assets, get_expiring_warranties, get_unassigned_assets,search_assets
from datetime import datetime

@tool
def get_asset_tool(asset_id: int = None,
    asset_tag: str = None,
    serial_number: str = None):
    """
    Retrieves an assets information given whether asset_id or asset_tag and serial_number of the asset
    Args:
        asset_id (int, optional): _description_. Defaults to None.
        asset_tag (str, optional): _description_. Defaults to None.
        serial_number (str, optional): _description_. Defaults to None.
    """
    return get_asset(asset_id,asset_tag,serial_number)

@tool
def get_asset_stats_tool(asset_type: str = None,
    status: str = None,
    condition: str = None):
    """
    Retrieves asset stats like total number of assets, their total cost, and their average cost based on different arguments like asset_type,status, andcondition.

    Args:
        asset_type (str, optional): _description_. Defaults to None.
        status (str, optional): _description_. Defaults to None.
        condition (str, optional): _description_. Defaults to None.
    """
    return get_asset_stats(asset_type,
    status,
    condition)
    
@tool
def get_employee_assets_tool(employee_id: int):
    """
    Get all the assets owned by an employee given their id

    Args:
        employee_id (int): _description_
    """
    return get_employee_assets(employee_id)

@tool
def get_expiring_warranties_tool(expiry_from: datetime = None,
    expiry_to: datetime = None):
    """
    Retrieves all the assets whose warranties are getting expired between the two dates as mentioned in arguments:

    Args:
        expiry_from (datetime, optional): _description_. Defaults to None.
        expiry_to (datetime, optional): _description_. Defaults to None.
    """
    return get_expiring_warranties(expiry_from,expiry_to)

@tool
def get_unassigned_assets_tool(asset_type: str = None,
    status: str = None,
    condition: str = None):
    """
    Retrieves all the assets which have not yet been assigned to anyone and are available filtered on following args:
    Args:
        asset_type (_type_): _description_
        status (_type_): _description_
        condition (_type_): _description_
    """
    return get_unassigned_assets(asset_type,
    status,
    condition)
    
@tool
def search_assets_tool(asset_type: str = None,
    brand: str = None,
    model: str = None,
    status: str = None,
    condition: str = None,
    assigned_to: int = None,
    purchase_cost_min: float = None,
    purchase_cost_max: float = None,
    purchase_from: datetime = None,
    purchase_to: datetime = None,
    warranty_from: datetime = None,
    warranty_to: datetime = None):
    """
    Retrieves assets that match the following criteria given by the arguments:
    Args:
        asset_type (str, optional): _description_. Defaults to None.
        brand (str, optional): _description_. Defaults to None.
        model (str, optional): _description_. Defaults to None.
        status (str, optional): _description_. Defaults to None.
        condition (str, optional): _description_. Defaults to None.
        assigned_to (int, optional): _description_. Defaults to None.
        purchase_cost_min (float, optional): _description_. Defaults to None.
        purchase_cost_max (float, optional): _description_. Defaults to None.
        purchase_from (datetime, optional): _description_. Defaults to None.
        purchase_to (datetime, optional): _description_. Defaults to None.
        warranty_from (datetime, optional): _description_. Defaults to None.
        warranty_to (datetime, optional): _description_. Defaults to None.
    """
    return search_assets(asset_type,
    brand,
    model,
    status,
    condition,
    assigned_to,
    purchase_cost_min,
    purchase_cost_max,
    purchase_from,
    purchase_to,
    warranty_from,
    warranty_to)