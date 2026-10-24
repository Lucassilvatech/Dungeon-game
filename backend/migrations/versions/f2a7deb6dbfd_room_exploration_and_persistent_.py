"""room exploration and persistent discovery"""
from alembic import op
import sqlalchemy as sa

revision = 'f2a7deb6dbfd'
down_revision = '234126160af2'
branch_labels = None
depends_on = None

ROOM_DATA = [{'id': 'city1', 'floor_id': 1, 'name': 'Vila do Alvorecer', 'kind': 'CITY', 'seed': 0, 'owner_id': None, 'data': {'width': 28, 'height': 20, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [1, 0], [1, 19], [2, 0], [2, 19], [3, 0], [3, 19], [4, 0], [4, 19], [5, 0], [5, 19], [6, 0], [6, 19], [7, 0], [7, 19], [8, 0], [8, 19], [9, 0], [9, 19], [10, 0], [10, 19], [11, 0], [11, 19], [12, 0], [12, 19], [13, 0], [13, 19], [14, 0], [14, 19], [15, 0], [15, 19], [16, 0], [16, 19], [17, 0], [17, 19], [18, 0], [18, 19], [19, 0], [19, 19], [20, 0], [20, 19], [21, 0], [21, 19], [22, 0], [22, 19], [23, 0], [23, 19], [24, 0], [24, 19], [25, 0], [25, 19], [26, 0], [26, 19], [27, 0], [27, 1], [27, 2], [27, 3], [27, 4], [27, 5], [27, 6], [27, 7], [27, 8], [27, 9], [27, 10], [27, 11], [27, 12], [27, 13], [27, 14], [27, 15], [27, 16], [27, 17], [27, 18], [27, 19], [7, 3], [7, 4], [7, 5], [7, 6], [8, 3], [8, 4], [8, 5], [8, 6], [9, 3], [9, 4], [9, 5], [9, 6], [10, 3], [10, 4], [10, 5], [10, 6], [11, 3], [11, 4], [11, 5], [11, 6], [12, 3], [12, 4], [12, 5], [12, 6], [17, 4], [17, 5], [17, 6], [17, 7], [18, 4], [18, 5], [18, 6], [18, 7], [19, 4], [19, 5], [19, 6], [19, 7], [20, 4], [20, 5], [20, 6], [20, 7], [21, 4], [21, 5], [21, 6], [21, 7]], 'npc': (3, 3), 'monsters': {}, 'portal': [24, 3], 'theme': 'city', 'resources': [], 'difficulty': 1, 'buildings': [{'x': 7, 'y': 3, 'width': 6, 'height': 4, 'name': 'Guilda'}, {'x': 17, 'y': 4, 'width': 5, 'height': 4, 'name': 'Mercado · em breve'}]}}, {'id': 'guild', 'floor_id': 1, 'name': 'Guilda · Recepção', 'kind': 'GUILD', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': [3, 3], 'monsters': {}, 'portal': None, 'theme': 'interior', 'resources': [], 'difficulty': 1}}, {'id': 'training', 'floor_id': 1, 'name': 'Pátio de treinamento', 'kind': 'TRAINING', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': [3, 3], 'monsters': {'dummy': (10, 6)}, 'portal': None, 'theme': 'interior', 'resources': [], 'difficulty': 1}}, {'id': 'common_a', 'floor_id': 1, 'name': 'Bosque das lanternas', 'kind': 'COMMON', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': (3, 3), 'monsters': {'slime': (5, 6)}, 'portal': None, 'theme': 'forest', 'resources': [], 'difficulty': 1}}, {'id': 'common_b', 'floor_id': 1, 'name': 'Trilha dos vagalumes', 'kind': 'COMMON', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': (3, 3), 'monsters': {'slime': (5, 6)}, 'portal': None, 'theme': 'forest', 'resources': [], 'difficulty': 1}}, {'id': 'combat', 'floor_id': 1, 'name': 'Clareira dos ecos', 'kind': 'COMBAT', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': (3, 3), 'monsters': {'slime': (5, 6)}, 'portal': None, 'theme': 'forest', 'resources': [], 'difficulty': 1}}, {'id': 'boss', 'floor_id': 1, 'name': 'Santuário do Guardião', 'kind': 'BOSS', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': None, 'monsters': {'boss': (12, 8)}, 'portal': None, 'theme': 'ruins', 'resources': [], 'difficulty': 'EXTREMA', 'recommended_level': 3, 'recommended_group': 4}}, {'id': 'secret', 'floor_id': 1, 'name': 'Cripta da Maré Antiga', 'kind': 'SECRET_DUNGEON', 'seed': 0, 'owner_id': None, 'data': {'width': 16, 'height': 12, 'walls': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (0, 11), (1, 0), (1, 11), (2, 0), (2, 11), (3, 0), (3, 11), (4, 0), (4, 11), (5, 0), (5, 11), (6, 0), (6, 11), (7, 0), (7, 2), (7, 3), (7, 4), (7, 6), (7, 7), (7, 8), (7, 11), (8, 0), (8, 11), (9, 0), (9, 11), (10, 0), (10, 11), (11, 0), (11, 11), (12, 0), (12, 11), (13, 0), (13, 11), (14, 0), (14, 11), (15, 0), (15, 1), (15, 2), (15, 3), (15, 4), (15, 5), (15, 6), (15, 7), (15, 8), (15, 9), (15, 10), (15, 11)], 'npc': None, 'monsters': {'warden': (10, 7)}, 'portal': None, 'theme': 'water', 'resources': [], 'difficulty': 'PERIGOSA', 'recommended_level': 8, 'enemy_level': 8, 'enemy_hp': 65, 'enemy_attack': 14}}, {'id': 'city2', 'floor_id': 2, 'name': 'Mirante das Nuvens', 'kind': 'CITY', 'seed': 0, 'owner_id': None, 'data': {'width': 28, 'height': 20, 'walls': [[0, 0], [0, 1], [0, 2], [0, 3], [0, 4], [0, 5], [0, 6], [0, 7], [0, 8], [0, 9], [0, 10], [0, 11], [0, 12], [0, 13], [0, 14], [0, 15], [0, 16], [0, 17], [0, 18], [0, 19], [1, 0], [1, 19], [2, 0], [2, 19], [3, 0], [3, 19], [4, 0], [4, 19], [5, 0], [5, 19], [6, 0], [6, 19], [7, 0], [7, 19], [8, 0], [8, 19], [9, 0], [9, 19], [10, 0], [10, 19], [11, 0], [11, 19], [12, 0], [12, 19], [13, 0], [13, 19], [14, 0], [14, 19], [15, 0], [15, 19], [16, 0], [16, 19], [17, 0], [17, 19], [18, 0], [18, 19], [19, 0], [19, 19], [20, 0], [20, 19], [21, 0], [21, 19], [22, 0], [22, 19], [23, 0], [23, 19], [24, 0], [24, 19], [25, 0], [25, 19], [26, 0], [26, 19], [27, 0], [27, 1], [27, 2], [27, 3], [27, 4], [27, 5], [27, 6], [27, 7], [27, 8], [27, 9], [27, 10], [27, 11], [27, 12], [27, 13], [27, 14], [27, 15], [27, 16], [27, 17], [27, 18], [27, 19], [7, 3], [7, 4], [7, 5], [7, 6], [8, 3], [8, 4], [8, 5], [8, 6], [9, 3], [9, 4], [9, 5], [9, 6], [10, 3], [10, 4], [10, 5], [10, 6], [11, 3], [11, 4], [11, 5], [11, 6], [12, 3], [12, 4], [12, 5], [12, 6], [17, 4], [17, 5], [17, 6], [17, 7], [18, 4], [18, 5], [18, 6], [18, 7], [19, 4], [19, 5], [19, 6], [19, 7], [20, 4], [20, 5], [20, 6], [20, 7], [21, 4], [21, 5], [21, 6], [21, 7]], 'npc': (3, 3), 'monsters': {}, 'portal': [24, 3], 'theme': 'city', 'resources': [], 'difficulty': 1, 'buildings': [{'x': 7, 'y': 3, 'width': 6, 'height': 4, 'name': 'Guilda'}, {'x': 17, 'y': 4, 'width': 5, 'height': 4, 'name': 'Mercado · em breve'}]}}]

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('floors',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('rooms',
    sa.Column('id', sa.String(length=80), nullable=False),
    sa.Column('floor_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('kind', sa.String(length=30), nullable=False),
    sa.Column('seed', sa.Integer(), nullable=False),
    sa.Column('owner_id', sa.Integer(), nullable=True),
    sa.Column('data', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['floor_id'], ['floors.id'], ),
    sa.ForeignKeyConstraint(['owner_id'], ['characters.id'], name='fk_room_owner', use_alter=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('room_connections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=80), nullable=False),
    sa.Column('target', sa.String(length=80), nullable=False),
    sa.Column('x', sa.Integer(), nullable=False),
    sa.Column('y', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['source'], ['rooms.id'], ),
    sa.ForeignKeyConstraint(['target'], ['rooms.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source', 'target')
    )
    op.create_table('raids',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('leader_id', sa.Integer(), nullable=False),
    sa.Column('invite', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['leader_id'], ['characters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('invite')
    )
    op.create_table('room_states',
    sa.Column('character_id', sa.Integer(), nullable=False),
    sa.Column('room_id', sa.String(length=80), nullable=False),
    sa.Column('completed', sa.Boolean(), nullable=False),
    sa.Column('visits', sa.Integer(), nullable=False),
    sa.Column('codex', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
    sa.PrimaryKeyConstraint('character_id', 'room_id')
    )
    op.create_table('raid_members',
    sa.Column('raid_id', sa.Integer(), nullable=False),
    sa.Column('character_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ),
    sa.ForeignKeyConstraint(['raid_id'], ['raids.id'], ),
    sa.PrimaryKeyConstraint('raid_id', 'character_id')
    )
    # Frozen initial room definitions: migration must not import mutable game rules.
    floors = sa.table('floors', sa.column('id',sa.Integer), sa.column('name',sa.String))
    op.bulk_insert(floors, [{'id':1,'name':'Andar 1'},{'id':2,'name':'Andar 2'}])
    rooms = sa.table('rooms',sa.column('id',sa.String),sa.column('floor_id',sa.Integer),sa.column('name',sa.String),sa.column('kind',sa.String),sa.column('seed',sa.Integer),sa.column('owner_id',sa.Integer),sa.column('data',sa.JSON))
    op.bulk_insert(rooms, ROOM_DATA)
    op.add_column('battles', sa.Column('room_id', sa.String(length=80), nullable=True))
    op.add_column('battles', sa.Column('reward_amount', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_battle_room', 'battles', 'rooms', ['room_id'], ['id'])
    op.add_column('characters', sa.Column('room_id', sa.String(length=80), server_default='city1', nullable=False))
    op.execute("UPDATE characters SET room_id = CASE WHEN floor = 2 THEN 'city2' ELSE 'common_a' END")
    op.execute("UPDATE battles SET room_id = characters.room_id FROM characters WHERE battles.character_id = characters.id")
    op.create_foreign_key('fk_character_room', 'characters', 'rooms', ['room_id'], ['id'])
    # ### end Alembic commands ###

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('fk_character_room', 'characters', type_='foreignkey')
    op.drop_column('characters', 'room_id')
    op.drop_constraint('fk_battle_room', 'battles', type_='foreignkey')
    op.drop_column('battles', 'reward_amount')
    op.drop_column('battles', 'room_id')
    op.drop_table('raid_members')
    op.drop_table('room_states')
    op.drop_table('raids')
    op.drop_table('room_connections')
    op.drop_table('rooms')
    op.drop_table('floors')
    # ### end Alembic commands ###
