"""add department-scoped announcement title uniqueness

Revision ID: 79c68f2a1d34
Revises: 4689b85c13b6
Create Date: 2026-10-02 17:54:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "79c68f2a1d34"
down_revision: Union[str, Sequence[str], None] = "4689b85c13b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_announcements_title_department_id",
        "announcements",
        ["title", "department_id"],
        unique=True
    )


def downgrade() -> None:
    op.drop_index(
        "uq_announcements_title_department_id",
        table_name="announcements"
    )
