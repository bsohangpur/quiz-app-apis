"""initial schema

Revision ID: initial_schema
Revises: 
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create sessions table
    op.create_table('sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create questions table
    op.create_table('questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('options', sa.Text(), nullable=True),
        sa.Column('match_the_following_pairs', sa.Text(), nullable=True),
        sa.Column('sequence_items', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('questions')
    op.drop_table('sessions')
    op.drop_table('users') 