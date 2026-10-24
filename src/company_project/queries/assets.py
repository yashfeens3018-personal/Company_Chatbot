from sqlalchemy import select, func, insert, update, delete
from datetime import datetime

from ..models import Assets, Employees
from ..database import SessionLocal


asset_statuses = [
    "available",
    "assigned",
    "in_repair",
    "lost",
    "disposed"
]

asset_conditions = [
    "excellent",
    "good",
    "fair",
    "poor",
    "damaged"
]

def get_asset(
    asset_id: int = None,
    asset_tag: str = None,
    serial_number: str = None
):
    if asset_id is None and asset_tag is None and serial_number is None:
        raise ValueError(
            "Provide asset ID, asset tag, or serial number."
        )

    if sum(
        value is not None
        for value in [asset_id, asset_tag, serial_number]
    ) > 1:
        raise ValueError(
            "Provide only one of asset ID, asset tag, or serial number."
        )

    if asset_id is not None:
        does_asset_id_exist(asset_id=asset_id)
        condition = Assets.asset_id == asset_id
    elif asset_tag is not None:
        does_asset_tag_exist(asset_tag=asset_tag)
        condition = Assets.asset_tag == asset_tag
    else:
        does_asset_serial_exist(asset_serial=serial_number)
        condition = Assets.serial_number == serial_number

    stmt = select(
        Assets.asset_id,
        Assets.asset_tag,
        Assets.asset_type,
        Assets.brand,
        Assets.model,
        Assets.serial_number,
        Assets.purchase_date,
        Assets.purchase_cost,
        Assets.status,
        Assets.assigned_to,
        Assets.condition,
        Assets.warranty_expiry,
        Assets.created_at
    ).where(condition)

    with SessionLocal() as session:
        result = session.execute(stmt)
        asset = [dict(row._mapping) for row in result.all()]

    return asset


def search_assets(
    asset_type: str = None,
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
    warranty_to: datetime = None
):
    conditions = []

    if asset_type is not None:
        conditions.append(
            Assets.asset_type.ilike(f"%{asset_type}%")
        )

    if brand is not None:
        conditions.append(
            Assets.brand.ilike(f"%{brand}%")
        )

    if model is not None:
        conditions.append(
            Assets.model.ilike(f"%{model}%")
        )

    if status is not None:
        if status not in asset_statuses:
            raise ValueError(
                f"Status '{status}' is not one of the allowed statuses "
                f"{', '.join(asset_statuses)}"
            )      
        status = status.lower()
        conditions.append(Assets.status == status)

    if condition is not None:
        if condition not in asset_conditions:
            raise ValueError(
                f"Condition '{condition}' is not one of the allowed conditions "
                f"{', '.join(asset_conditions)}"
            )
        condition = condition.lower()
        conditions.append(Assets.condition == condition)

    if assigned_to is not None:
        conditions.append(Assets.assigned_to == assigned_to)

    if purchase_cost_min is not None:
        conditions.append(
            Assets.purchase_cost >= purchase_cost_min
        )

    if purchase_cost_max is not None:
        conditions.append(
            Assets.purchase_cost <= purchase_cost_max
        )

    if purchase_from is not None:
        conditions.append(
            Assets.purchase_date >= purchase_from
        )

    if purchase_to is not None:
        conditions.append(
            Assets.purchase_date <= purchase_to
        )

    if warranty_from is not None:
        conditions.append(
            Assets.warranty_expiry >= warranty_from
        )

    if warranty_to is not None:
        conditions.append(
            Assets.warranty_expiry <= warranty_to
        )

    stmt = select(
        Assets.asset_id,
        Assets.asset_tag,
        Assets.asset_type,
        Assets.brand,
        Assets.model,
        Assets.serial_number,
        Assets.purchase_date,
        Assets.purchase_cost,
        Assets.status,
        Assets.assigned_to,
        Assets.condition,
        Assets.warranty_expiry
    ).where(*conditions)

    with SessionLocal() as session:
        result = session.execute(stmt)
        assets = [dict(row._mapping) for row in result.all()]

    return assets


def get_employee_assets(employee_id: int):
    stmt = select(
        Assets.asset_id,
        Assets.asset_tag,
        Assets.asset_type,
        Assets.brand,
        Assets.model,
        Assets.serial_number,
        Assets.status,
        Assets.condition,
        Assets.purchase_date,
        Assets.warranty_expiry
    ).where(
        Assets.assigned_to == employee_id
    )
    does_employee_exist(employee_id=employee_id)

    with SessionLocal() as session:
        result = session.execute(stmt)
        assets = [dict(row._mapping) for row in result.all()]

    return assets


def get_unassigned_assets(
    asset_type: str = None,
    status: str = None,
    condition: str = None
):
    conditions = [
        Assets.assigned_to.is_(None)
    ]

    if asset_type is not None:
        conditions.append(
            Assets.asset_type == asset_type
        )

    if status is not None:
        if status not in asset_statuses:
            raise ValueError(
                f"Status '{status}' is not one of the allowed statuses "
                f"{', '.join(asset_statuses)}"
            )      
        status = status.lower()
        conditions.append(Assets.status == status)
    
    if condition is not None:
        if condition not in asset_conditions:
            raise ValueError(
                f"Condition '{condition}' is not one of the allowed conditions "
                f"{', '.join(asset_conditions)}"
            )
        condition = condition.lower()
        conditions.append(Assets.condition == condition)

    stmt = select(
        Assets.asset_id,
        Assets.asset_tag,
        Assets.asset_type,
        Assets.brand,
        Assets.model,
        Assets.serial_number,
        Assets.status,
        Assets.condition,
        Assets.purchase_date,
        Assets.warranty_expiry
    ).where(*conditions)

    with SessionLocal() as session:
        result = session.execute(stmt)
        assets = [dict(row._mapping) for row in result.all()]

    return assets


def get_expiring_warranties(
    expiry_from: datetime = None,
    expiry_to: datetime = None
):
    conditions = [
        Assets.warranty_expiry.is_not(None)
    ]

    if expiry_from is not None:
        conditions.append(
            Assets.warranty_expiry >= expiry_from
        )

    if expiry_to is not None:
        conditions.append(
            Assets.warranty_expiry <= expiry_to
        )

    stmt = select(
        Assets.asset_id,
        Assets.asset_tag,
        Assets.asset_type,
        Assets.brand,
        Assets.model,
        Assets.assigned_to,
        Assets.warranty_expiry
    ).where(
        *conditions
    ).order_by(
        Assets.warranty_expiry.asc()
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        assets = [dict(row._mapping) for row in result.all()]

    return assets


def get_asset_stats(
    asset_type: str = None,
    status: str = None,
    condition: str = None
):
    conditions = []

    if asset_type is not None:
        conditions.append(
            Assets.asset_type == asset_type
        )

    if status is not None:
        status = status.lower()
        conditions.append(
            Assets.status == status
        )

    if condition is not None:
        condition = condition.lower()
        conditions.append(
            Assets.condition == condition
        )

    stmt = select(
        func.count(Assets.asset_id).label("Total Assets"),
        func.sum(Assets.purchase_cost).label("Total Purchase Cost"),
        func.avg(Assets.purchase_cost).label("Average Purchase Cost")
    ).where(*conditions)

    with SessionLocal() as session:
        result = session.execute(stmt)
        stats = [dict(row._mapping) for row in result.all()]

    return stats





def does_asset_tag_exist(
    asset_tag: str,
    exclude_id: int = None
):
    stmt = select(Assets.asset_id).where(
        Assets.asset_tag == asset_tag
    )

    if exclude_id is not None:
        stmt = stmt.where(
            Assets.asset_id != exclude_id
        )

    with SessionLocal() as session:
        result = session.execute(stmt)
        result = result.one_or_none()

    if result is not None:
        raise ValueError(
            f"Asset tag {asset_tag} already exists."
        )


def does_asset_id_exist(asset_id: int):
    stmt = select(Assets.asset_id).where(
        Assets.asset_id == asset_id
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        result = result.one_or_none()

    if result is None:
        raise LookupError(
            f"Asset id {asset_id} does not exist."
        )


def does_asset_serial_exist(
    asset_serial: str,
    exclude_id: int = None
):
    stmt = select(Assets.asset_id).where(
        Assets.serial_number == asset_serial
    )

    if exclude_id is not None:
        stmt = stmt.where(
            Assets.asset_id != exclude_id
        )

    with SessionLocal() as session:
        result = session.execute(stmt)
        result = result.one_or_none()

    if result is not None:
        raise ValueError(
            f"Asset serial number {asset_serial} already exists."
        )


def does_employee_exist(employee_id: int):
    stmt = select(Employees.employee_id).where(
        Employees.employee_id == employee_id
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        result = result.one_or_none()

    if result is None:
        raise LookupError(
            f"The employee with employee_id: {employee_id} does not exist."
        )


def status_employee_compatibility(
    status: str,
    assigned_to: int = None
):
    if status == "available" and assigned_to is not None:
        raise ValueError(
            "An available asset cannot be assigned to an employee."
        )

    if status == "assigned" and assigned_to is None:
        raise ValueError(
            "An assigned asset must have an assigned employee. Please provide an employee id."
        )

    if status in ["disposed", "lost"] and assigned_to is not None:
        raise ValueError(
            f"A {status} asset cannot be assigned to an employee."
        )


def create_asset(
    asset_tag: str,
    asset_type: str,
    serial_number: str,
    status: str,
    condition: str,
    brand: str = None,
    model: str = None,
    purchase_date: datetime = None,
    purchase_cost: float = None,
    assigned_to: int = None,
    warranty_expiry: datetime = None
):
    does_asset_tag_exist(asset_tag)
    does_asset_serial_exist(serial_number)

    status = status.lower()
    condition = condition.lower()

    if status not in asset_statuses:
        raise ValueError(
            f"Status '{status}' is not one of the allowed statuses "
            f"{', '.join(asset_statuses)}"
        )

    if condition not in asset_conditions:
        raise ValueError(
            f"Condition '{condition}' is not one of the allowed conditions "
            f"{', '.join(asset_conditions)}"
        )

    if assigned_to is not None:
        does_employee_exist(assigned_to)

    status_employee_compatibility(
        status=status,
        assigned_to=assigned_to
    )

    if (
        purchase_date is not None
        and warranty_expiry is not None
        and purchase_date > warranty_expiry
    ):
        raise ValueError(
            "Purchase date cannot be later than the warranty expiry date."
        )

    stmt = insert(Assets).values(
        asset_tag=asset_tag,
        asset_type=asset_type,
        brand=brand,
        model=model,
        serial_number=serial_number,
        purchase_date=purchase_date,
        purchase_cost=purchase_cost,
        status=status,
        assigned_to=assigned_to,
        condition=condition,
        warranty_expiry=warranty_expiry
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()
        asset_id = result.inserted_primary_key[0]

    return f"New asset with Asset id: {asset_id} has been updated successfully!"


def update_asset(
    id: int,
    asset_tag: str = None,
    asset_type: str = None,
    brand: str = None,
    model: str = None,
    serial_number: str = None,
    purchase_date: datetime = None,
    purchase_cost: float = None,
    status: str = None,
    assigned_to: int = None,
    condition: str = None,
    warranty_expiry: datetime = None,
    assigned_to_provided:bool=False
):
    does_asset_id_exist(id)
    stmt = select(
        Assets.asset_tag,
        Assets.asset_type,
        Assets.brand,
        Assets.model,
        Assets.serial_number,
        Assets.purchase_date,
        Assets.purchase_cost,
        Assets.status,
        Assets.assigned_to,
        Assets.condition,
        Assets.warranty_expiry
    ).where(
        Assets.asset_id == id
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        current_asset = result.one()

    values = {}

    if asset_tag is not None:
        does_asset_tag_exist(
            asset_tag,
            exclude_id=id
        )
        values["asset_tag"] = asset_tag

    if asset_type is not None:
        values["asset_type"] = asset_type

    if brand is not None:
        values["brand"] = brand

    if model is not None:
        values["model"] = model


    if serial_number is not None:
        does_asset_serial_exist(
            serial_number,
            exclude_id=id
        )
        values["serial_number"] = serial_number

    if purchase_cost is not None:
        values["purchase_cost"] = purchase_cost
        
    if status is not None:
        status = status.lower()

        if status not in asset_statuses:
            raise ValueError(
                f"Status '{status}' is not one of the allowed statuses "
                f"{', '.join(asset_statuses)}"
            )
    if assigned_to is not None:
        does_employee_exist(assigned_to)
        values["assigned_to"] = assigned_to

    if condition is not None:
        condition = condition.lower()

        if condition not in asset_conditions:
            raise ValueError(
                f"Condition '{condition}' is not one of the allowed conditions "
                f"{', '.join(asset_conditions)}"
            )

        values["condition"] = condition

    final_status = (
        status
        if status is not None
        else current_asset.status
    )

    final_assigned_to = (
        assigned_to
        if assigned_to_provided 
        else current_asset.assigned_to
    )

    final_purchase_date = (
        purchase_date
        if purchase_date is not None
        else current_asset.purchase_date
    )

    final_warranty_expiry = (
        warranty_expiry
        if warranty_expiry is not None
        else current_asset.warranty_expiry
    )

    status_employee_compatibility(
        status=final_status,
        assigned_to=final_assigned_to
    )
    
    if status in ["lost", "disposed", "available"]:
        if assigned_to is not None:
            raise ValueError(f"A {status} asset cannot be assigned to an employee.")
        values["status"] = status
        values["assigned_to"] = None
    elif status is not None:
        values["status"] = status
        if assigned_to is not None:
            does_employee_exist(assigned_to)
            values["assigned_to"] = assigned_to


    if (
        final_purchase_date is not None
        and final_warranty_expiry is not None
        and final_purchase_date > final_warranty_expiry
    ):
        raise ValueError(
            "Purchase date cannot be later than the warranty expiry date."
        )

    if purchase_date is not None:
        values["purchase_date"] = purchase_date

    if warranty_expiry is not None:
        values["warranty_expiry"] = warranty_expiry

    

    if not values:
        return 0

    stmt = update(Assets).where(
        Assets.asset_id == id
    ).values(**values)

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()

    return f"Asset id: {id} has been updated successfully!"


def delete_asset(id: int):
    stmt = delete(Assets).where(
        Assets.asset_id == id
    )

    with SessionLocal() as session:
        result = session.execute(stmt)
        session.commit()

    if result.rowcount == 0:
        raise ValueError(
            f"Asset id: {id} does not exist."
        )
    else:
        return f"Asset with asset id: {id} has been deleted successfully!"
