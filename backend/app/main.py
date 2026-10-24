import secrets
from datetime import datetime, timedelta
from typing import Literal
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from .database import get_db
from .models import Account, Character, Item, Battle, LinkCode
from .security import current_account, password_hash, password_matches, issue_token, digest
from .config import settings
from . import game

app=FastAPI(title="Tower RPG",version="0.1.0")

@app.exception_handler(IntegrityError)
async def conflict(request,exc):
    return JSONResponse(status_code=409,content={"detail":"Nome ou operação já existente"})

class Credentials(BaseModel):
    username: str = Field(min_length=3,max_length=40,pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8,max_length=128)
class CharacterInput(BaseModel):
    name: str = Field(min_length=2,max_length=30,pattern=r"^[\w -]+$")
class Move(BaseModel):
    dx: int = Field(ge=-1,le=1)
    dy: int = Field(ge=-1,le=1)
class Start(BaseModel):
    monster: Literal["slime","boss"]
class Action(BaseModel):
    turn: int = Field(ge=0)
    action: Literal["attack","skill","defend"]
class Travel(BaseModel):
    floor: int

@app.get("/health")
def health(db=Depends(get_db)):
    from sqlalchemy import text
    db.execute(text("SELECT 1"));return {"status":"ok"}

@app.post("/auth/register",status_code=201)
def register(body:Credentials,db=Depends(get_db)):
    a=Account(username=body.username.lower(),password=password_hash(body.password));db.add(a);db.flush()
    return issue_token(db,a)

@app.post("/auth/login")
def login(body:Credentials,db=Depends(get_db)):
    a=db.scalar(select(Account).where(Account.username==body.username.lower()))
    if not a or not password_matches(body.password,a.password): raise HTTPException(401,"Credenciais inválidas")
    return issue_token(db,a)

@app.post("/character",status_code=201)
def create(body:CharacterInput,a=Depends(current_account),db=Depends(get_db)):
    c=Character(account_id=a.id,name=body.name);db.add(c);db.flush()
    db.add(Item(owner=c.id,definition="sword",quantity=1));db.flush()
    return game.snapshot(db,c)

@app.get("/state")
def state(a=Depends(current_account),db=Depends(get_db)):
    return game.snapshot(db,game.character(db,a))

@app.post("/move")
def move(body:Move,a=Depends(current_account),db=Depends(get_db)):
    c=game.character(db,a);game.move(db,c,body.dx,body.dy);return game.snapshot(db,c)

@app.post("/interact")
def interact(a=Depends(current_account),db=Depends(get_db)):
    return game.interact(db,game.character(db,a))

@app.post("/travel")
def travel(body:Travel,a=Depends(current_account),db=Depends(get_db)):
    c=game.character(db,a);game.travel(db,c,body.floor);return game.snapshot(db,c)

@app.post("/battles")
def start(body:Start,a=Depends(current_account),db=Depends(get_db)):
    return game.start_battle(db,game.character(db,a),body.monster)

@app.post("/battles/{battle_id}/action")
def action(battle_id:int,body:Action,a=Depends(current_account),db=Depends(get_db)):
    return game.action(db,game.character(db,a),battle_id,body.turn,body.action)

@app.get("/rewards")
def rewards(a=Depends(current_account),db=Depends(get_db)):
    c=game.character(db,a)
    return [game.battle_data(b) for b in db.scalars(select(Battle).where(Battle.character_id==c.id,Battle.status=="won",Battle.claimed==False))]

@app.post("/battles/{battle_id}/claim")
def claim(battle_id:int,a=Depends(current_account),db=Depends(get_db)):
    return game.claim(db,game.character(db,a),battle_id)

@app.post("/inventory/{item_id}/equip")
def equip(item_id:int,a=Depends(current_account),db=Depends(get_db)):
    c=game.character(db,a);game.equip(db,c,item_id);db.flush();return game.snapshot(db,c)

@app.post("/discord/code")
def link_code(a=Depends(current_account),db=Depends(get_db)):
    # Lock account to serialize code replacement.
    db.scalar(select(Account).where(Account.id==a.id).with_for_update())
    old=db.scalar(select(LinkCode).where(LinkCode.account_id==a.id))
    if old: db.delete(old);db.flush()
    code=secrets.token_urlsafe(12)
    db.add(LinkCode(code=digest(code),account_id=a.id,expires=datetime.utcnow()+timedelta(minutes=5)))
    return {"code":code,"expires_in":300}

def bot_access(x_bot_key:str=Header(default="")):
    if not settings.discord_service_key or not secrets.compare_digest(x_bot_key,settings.discord_service_key):
        raise HTTPException(403,"Acesso do bot não autorizado")

class Link(BaseModel):
    code:str
    discord_id:str = Field(pattern=r"^[0-9]{1,30}$")

@app.post("/discord/link",dependencies=[Depends(bot_access)])
def link(body:Link,db=Depends(get_db)):
    code=db.scalar(select(LinkCode).where(LinkCode.code==digest(body.code)).with_for_update())
    if not code or code.expires<datetime.utcnow(): raise HTTPException(400,"Código inválido ou expirado")
    a=db.get(Account,code.account_id);a.discord_id=body.discord_id;db.delete(code)
    return {"linked":True}

@app.get("/discord/{discord_id}/state",dependencies=[Depends(bot_access)])
def discord_state(discord_id:str,db=Depends(get_db)):
    a=db.scalar(select(Account).where(Account.discord_id==discord_id))
    if not a: raise HTTPException(404,"Use /vincular primeiro")
    return game.snapshot(db,game.character(db,a))
