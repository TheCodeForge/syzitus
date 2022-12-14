"""empty message

Revision ID: 14e8dcab2bb8
Revises: 7a6f57f52371
Create Date: 2022-10-21 12:57:48.607864

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import FetchedValue


# revision identifiers, used by Alembic.
revision = '14e8dcab2bb8'
down_revision = '7a6f57f52371'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('images')
    op.drop_index('badpic_phash_trgm_idx', table_name='badpics')
    op.drop_index('badpics_phash_index', table_name='badpics')
    op.create_index('badpics_phash_trgm_idx', 'badpics', ['phash'], unique=False, postgresql_using='gin', postgresql_ops={'phash': 'gin_trgm_ops'})
    op.create_index(op.f('ix_badpics_phash'), 'badpics', ['phash'], unique=False)
    op.drop_index('boards_name_trgm_idx', table_name='boards')
    op.drop_column('boards', 'motd')
    op.drop_column('boards', 'hide_banner_data')
    op.drop_column('boards', 'public_chat')
    op.drop_column('comments', 'board_id')
    op.drop_index('comment_body_trgm_idx', table_name='comments_aux')
    op.create_index('comments_aux_body_trgm_idx', 'comments_aux', ['body'], unique=False, postgresql_using='gin', postgresql_ops={'body': 'gin_trgm_ops'})
    op.drop_index('domains_domain_trgm_idx', table_name='domains')
    op.drop_index('submission_aux_url_trgm_idx', table_name='submissions_aux')
    op.drop_index('submissions_title_trgm_idx', table_name='submissions_aux')
    op.create_index('submissions_aux_title_trgm_idx', 'submissions_aux', ['title'], unique=False, postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    op.create_index('submissions_aux_url_trgm_idx', 'submissions_aux', ['url'], unique=False, postgresql_using='gin', postgresql_ops={'url': 'gin_trgm_ops'})
    op.create_index(op.f('ix_users_original_username'), 'users', ['original_username'], unique=False)
    op.drop_column('users', 'secondary_color')
    op.drop_column('users', 'color')
    op.drop_column('users', 'signature')
    op.drop_column('users', 'banner_set_utc')
    op.drop_column('users', 'signature_html')
    op.drop_column('users', 'profile_set_utc')
    op.drop_column('users', 'auto_join_chat')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('auto_join_chat', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('profile_set_utc', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('signature_html', sa.VARCHAR(length=512), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('banner_set_utc', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('signature', sa.VARCHAR(length=280), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('color', sa.VARCHAR(length=6), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('secondary_color', sa.VARCHAR(length=6), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_users_original_username'), table_name='users')
    op.drop_index('submissions_aux_url_trgm_idx', table_name='submissions_aux', postgresql_using='gin', postgresql_ops={'url': 'gin_trgm_ops'})
    op.drop_index('submissions_aux_title_trgm_idx', table_name='submissions_aux', postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    op.create_index('submissions_title_trgm_idx', 'submissions_aux', ['title'], unique=False)
    op.create_index('submission_aux_url_trgm_idx', 'submissions_aux', ['url'], unique=False)
    op.create_index('domains_domain_trgm_idx', 'domains', ['domain'], unique=False)
    op.drop_index('comments_aux_body_trgm_idx', table_name='comments_aux', postgresql_using='gin', postgresql_ops={'body': 'gin_trgm_ops'})
    op.create_index('comment_body_trgm_idx', 'comments_aux', ['body'], unique=False)
    op.add_column('comments', sa.Column('board_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('boards', sa.Column('public_chat', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('boards', sa.Column('hide_banner_data', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column('boards', sa.Column('motd', sa.VARCHAR(length=1000), autoincrement=False, nullable=True))
    op.create_index('boards_name_trgm_idx', 'boards', ['name'], unique=False)
    op.drop_index(op.f('ix_badpics_phash'), table_name='badpics')
    op.drop_index('badpics_phash_trgm_idx', table_name='badpics', postgresql_using='gin', postgresql_ops={'phash': 'gin_trgm_ops'})
    op.create_index('badpics_phash_index', 'badpics', ['phash'], unique=False)
    op.create_index('badpic_phash_trgm_idx', 'badpics', ['phash'], unique=False)
    op.create_table('images',
    sa.Column('id', sa.BIGINT(), autoincrement=True, nullable=False),
    sa.Column('state', sa.VARCHAR(length=8), autoincrement=False, nullable=True),
    sa.Column('number', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('text', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='images_pkey')
    )
    # ### end Alembic commands ###
