"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-20 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create complaint status enum
    complaint_status = postgresql.ENUM(
        'pending', 'processing', 'summarizing', 'completed', 'failed',
        name='complaintstatus'
    )
    complaint_status.create(op.get_bind())

    # Create document type enum
    document_type = postgresql.ENUM(
        'pdf', 'image', 'docx', 'doc', 'xls', 'xlsx',
        name='documenttype'
    )
    document_type.create(op.get_bind())

    # Create processing status enum
    processing_status = postgresql.ENUM(
        'pending', 'uploading', 'extracting', 'extracted', 'summarizing', 'completed', 'failed',
        name='processingstatus'
    )
    processing_status.create(op.get_bind())

    # Create summary type enum
    summary_type = postgresql.ENUM(
        'document', 'overall',
        name='summarytype'
    )
    summary_type.create(op.get_bind())

    # Create complaints table
    op.create_table(
        'complaints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('external_ref', sa.String(100), unique=True, index=True, nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('status', postgresql.ENUM(
            'pending', 'processing', 'summarizing', 'completed', 'failed',
            name='complaintstatus', create_type=False
        ), nullable=False, server_default='pending'),
        sa.Column('overall_summary', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('complaint_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('complaints.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(512), nullable=False),
        sa.Column('file_type', postgresql.ENUM(
            'pdf', 'image', 'docx', 'doc', 'xls', 'xlsx',
            name='documenttype', create_type=False
        ), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size', sa.BigInteger, nullable=False),
        sa.Column('extracted_text', sa.Text, nullable=True),
        sa.Column('processing_status', postgresql.ENUM(
            'pending', 'uploading', 'extracting', 'extracted', 'summarizing', 'completed', 'failed',
            name='processingstatus', create_type=False
        ), nullable=False, server_default='pending'),
        sa.Column('processing_progress', sa.String(50), nullable=True, server_default='0%'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('celery_task_id', sa.String(255), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create summaries table
    op.create_table(
        'summaries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('documents.id', ondelete='CASCADE'),
                  unique=True, index=True, nullable=True),
        sa.Column('complaint_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('complaints.id', ondelete='CASCADE'),
                  index=True, nullable=True),
        sa.Column('summary_type', postgresql.ENUM(
            'document', 'overall',
            name='summarytype', create_type=False
        ), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('tokens_used', sa.Integer, nullable=True),
        sa.Column('model_used', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('summaries')
    op.drop_table('documents')
    op.drop_table('complaints')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS summarytype')
    op.execute('DROP TYPE IF EXISTS processingstatus')
    op.execute('DROP TYPE IF EXISTS documenttype')
    op.execute('DROP TYPE IF EXISTS complaintstatus')
