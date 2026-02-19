"""THe Alembic was initionaly and the first migrate was created

Revision ID: e43e26898305
Revises: d803b952d66a
Create Date: 2026-02-12 12:27:05.316196

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e43e26898305"
down_revision: Union[str, Sequence[str], None] = "d803b952d66a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
