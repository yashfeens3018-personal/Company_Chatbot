"""add leave request validation constraints

Revision ID: 84bc106af231
Revises: 79c68f2a1d34
Create Date: 2026-10-02 22:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "84bc106af231"
down_revision: Union[str, Sequence[str], None] = "79c68f2a1d34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("leave_requests") as batch_op:
        batch_op.create_check_constraint(
            "ck_leave_requests_leave_type",
            "leave_type IN ('Annual', 'Sick', 'Casual', 'Unpaid', 'Maternity')"
        )
        batch_op.create_check_constraint(
            "ck_leave_requests_status",
            "status IN ('Pending', 'Approved', 'Rejected')"
        )
        batch_op.create_check_constraint(
            "ck_leave_requests_date_order",
            "start_date < end_date"
        )


def downgrade() -> None:
    with op.batch_alter_table("leave_requests") as batch_op:
        batch_op.drop_constraint(
            "ck_leave_requests_date_order",
            type_="check"
        )
        batch_op.drop_constraint(
            "ck_leave_requests_status",
            type_="check"
        )
        batch_op.drop_constraint(
            "ck_leave_requests_leave_type",
            type_="check"
        )
