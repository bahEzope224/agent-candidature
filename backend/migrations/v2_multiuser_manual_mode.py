"""
Migration : Support multi-utilisateur + mode manuel
-----------------------------------------------------
1. Ajout de hashed_password sur la table users
2. Ajout de followup_generated_at et followup_email_body sur applications
3. Mise à jour des anciens statuts vers les nouveaux
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ── 1. users : ajout hashed_password ──────────────────────────
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.String(255), nullable=True),
    )

    # ── 2. applications : nouveaux champs mode manuel ──────────────
    op.add_column(
        "applications",
        sa.Column("followup_generated_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "applications",
        sa.Column("followup_email_body", sa.Text(), nullable=True),
    )

    # ── 3. Migration des anciens statuts ───────────────────────────
    op.execute("""
        UPDATE applications SET status = 'to_apply'
        WHERE status IN ('draft', 'pending_review', 'ready_to_send')
    """)
    op.execute("""
        UPDATE applications SET status = 'follow_up_needed'
        WHERE status = 'follow_up_scheduled'
    """)
    op.execute("""
        UPDATE applications SET status = 'interview'
        WHERE status IN ('interview_proposed', 'interview_confirmed')
    """)


def downgrade():
    op.drop_column("users", "hashed_password")
    op.drop_column("applications", "followup_generated_at")
    op.drop_column("applications", "followup_email_body")
