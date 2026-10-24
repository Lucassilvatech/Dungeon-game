from sqlalchemy import select
from .database import Session
from .models import ItemDefinition, Treasury, Ledger
from .config import settings

def seed():
    if settings.initial_treasury < 0 or min(settings.monster_reward,settings.boss_reward)<0:
        raise ValueError('Parâmetros econômicos devem ser não negativos')
    with Session.begin() as db:
        # PostgreSQL transaction advisory lock serializes concurrent startup seeds.
        if db.bind.dialect.name == 'postgresql':
            from sqlalchemy import text
            db.execute(text('SELECT pg_advisory_xact_lock(7312026)'))
        from .rooms import seed_world
        seed_world(db)
        for key,name,kind,power in [('sword','Espada de aprendiz','weapon',3),('crystal','Cristal da clareira','material',0)]:
            if not db.get(ItemDefinition,key):
                db.add(ItemDefinition(id=key,name=name,kind=kind,power=power))
        if not db.get(Treasury,1):
            db.add(Treasury(id=1,balance=settings.initial_treasury))
            db.add(Ledger(reference='genesis',source='initial_supply',destination='treasury',amount=settings.initial_treasury))

if __name__=='__main__': seed()
