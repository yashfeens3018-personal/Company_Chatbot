from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from ..queries.assets import (
    get_asset,
    search_assets,
    get_employee_assets,
    get_unassigned_assets,
    get_expiring_warranties,
    get_asset_stats,
    create_asset,
    update_asset,
    delete_asset
)


router=APIRouter()


def _call_asset_query(query, *args, **kwargs):
    try:
        return query(*args, **kwargs)

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        ) from error

    except IntegrityError as error:
        raise HTTPException(
            status_code=409,
            detail="Asset data conflicts with existing records."
        ) from error


@router.get("/assets")
def get_assets_endpoint(asset_type: str = None,
    brand: str = None,
    model: str = None,
    status: str = None,
    condition: str = None,
    assigned_to_first_name: str = None,
    assigned_to_last_name: str = None,
    purchase_cost_min: float = None,
    purchase_cost_max: float = None,
    purchase_from: datetime = None,
    purchase_to: datetime = None,
    warranty_from: datetime = None,
    warranty_to: datetime = None):
    return _call_asset_query(search_assets,asset_type=asset_type,
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
    warranty_to=warranty_to)

@router.get("/assets/unassigned")
def get_unassigned_assets_endpoint(asset_type: str = None,
    status: str = None,
    condition: str = None):
    return _call_asset_query(
        get_unassigned_assets,
        asset_type=asset_type,
        status=status,
        condition=condition
    )


@router.get("/assets/warranties")
def get_expiring_warranties_endpoint():
    return _call_asset_query(
        get_expiring_warranties
    )


@router.get("/assets/stats")
def get_asset_stats_endpoint():
    return _call_asset_query(
        get_asset_stats
    )

@router.get("/assets/{asset_id}")
def get_asset_endpoint(asset_id: int):
    return _call_asset_query(
        get_asset,
        asset_id=asset_id
    )


@router.get("/assets/employee/{first_name}/{last_name}")
def get_employee_assets_endpoint(first_name: str, last_name: str):
    return _call_asset_query(
        get_employee_assets,
        first_name,
        last_name
    )


@router.delete("/assets/{asset_id}")
def delete_asset_endpoint(asset_id: int):
    return _call_asset_query(
        delete_asset,
        asset_id
    )


class UpdateAsset(BaseModel):
    id: int = Field(..., gt=0)
    asset_tag: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )
    asset_type: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )
    brand: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    serial_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    purchase_date: datetime | None = None
    purchase_cost: float | None = Field(
        default=None,
        ge=0
    )
    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )
    assigned_to_first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    assigned_to_last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    condition: str | None = Field(
        default=None,
        min_length=1,
        max_length=50
    )
    warranty_expiry: datetime | None = None


@router.put("/assets")
def update_asset_endpoint(asset: UpdateAsset):
    return _call_asset_query(
        update_asset,
        id=asset.id,
        asset_tag=asset.asset_tag,
        asset_type=asset.asset_type,
        brand=asset.brand,
        model=asset.model,
        serial_number=asset.serial_number,
        purchase_date=asset.purchase_date,
        purchase_cost=asset.purchase_cost,
        status=asset.status,
        assigned_to_first_name=asset.assigned_to_first_name,
        assigned_to_last_name=asset.assigned_to_last_name,
        condition=asset.condition,
        warranty_expiry=asset.warranty_expiry,
        assigned_to_provided = (
            "assigned_to_first_name" in asset.model_fields_set
            or "assigned_to_last_name" in asset.model_fields_set
        )
    )


class CreateAsset(BaseModel):
    asset_tag: str = Field(
        ...,
        min_length=1,
        max_length=50
    )
    asset_type: str = Field(
        ...,
        min_length=1,
        max_length=50
    )
    brand: str | None = Field(
        default=None,
        max_length=100
    )
    model: str | None = Field(
        default=None,
        max_length=100
    )
    serial_number: str = Field(
        ...,
        min_length=1,
        max_length=100
    )
    purchase_date: datetime | None = None
    purchase_cost: float | None = Field(
        default=None,
        ge=0
    )
    status: str = Field(
        ...,
        min_length=1,
        max_length=50
    )
    assigned_to_first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    assigned_to_last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )
    condition: str = Field(
        ...,
        min_length=1,
        max_length=50
    )
    warranty_expiry: datetime | None = None


@router.post("/assets")
def create_asset_endpoint(asset: CreateAsset):
    return _call_asset_query(
        create_asset,
        asset_tag=asset.asset_tag,
        asset_type=asset.asset_type,
        brand=asset.brand,
        model=asset.model,
        serial_number=asset.serial_number,
        purchase_date=asset.purchase_date,
        purchase_cost=asset.purchase_cost,
        status=asset.status,
        assigned_to_first_name=asset.assigned_to_first_name,
        assigned_to_last_name=asset.assigned_to_last_name,
        condition=asset.condition,
        warranty_expiry=asset.warranty_expiry
    )
