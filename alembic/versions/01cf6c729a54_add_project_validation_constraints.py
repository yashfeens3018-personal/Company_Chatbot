"""add project validation constraints

Revision ID: 01cf6c729a54
Revises: 84bc106af231
Create Date: 2026-10-02 23:50:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "01cf6c729a54"
down_revision: Union[str, Sequence[str], None] = "84bc106af231"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE projects
        SET status = CASE lower(trim(status))
            WHEN 'planning' THEN 'Planning'
            WHEN 'planned' THEN 'Planning'
            WHEN 'active' THEN 'Active'
            WHEN 'on hold' THEN 'On Hold'
            WHEN 'completed' THEN 'Completed'
            ELSE status
        END
        WHERE lower(trim(status)) IN (
            'planning', 'planned', 'active', 'on hold', 'completed'
        )
        """
    )
    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_check_constraint(
            "ck_projects_status",
            "status IN ('Planning', 'Active', 'On Hold', 'Completed')"
        )
        batch_op.create_check_constraint(
            "ck_projects_date_order",
            "expected_end_date IS NULL OR start_date < expected_end_date"
        )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint(
            "ck_projects_date_order",
            type_="check"
        )
        batch_op.drop_constraint(
            "ck_projects_status",
            type_="check"
        )
