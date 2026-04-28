from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Team, TeamPlayer, Player, WarSnapshot
from crud import upsert_war, set_manual_war
from scraper import fetch_war_leaders_bat, fetch_war_leaders_pit
from fastapi.middleware.cors import CORSMiddleware
from collections import defaultdict

Base.metadata.create_all(bind=engine)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- WAR ----------------

@app.post("/fetch-war")
def fetch_war(db: Session = Depends(get_db)):
    war_data = fetch_war_leaders_bat()

    print("=== BAT WAR KEYS ===")
    print(list(war_data.keys())[:20])

    players = db.query(Player).all()

    for p in players:
        if p.player_id in war_data:
            upsert_war(db, p.player_id, war_data[p.player_id], "bat")

    return {"status": "bat updated"}

@app.post("/fetch-war-pit")
def fetch_war_pit(db: Session = Depends(get_db)):
    war_data = fetch_war_leaders_pit()

    print("=== PIT WAR KEYS ===")
    print(list(war_data.keys())[:20])

    players = db.query(Player).all()

    for p in players:
        if p.player_id in war_data:
            upsert_war(db, p.player_id, war_data[p.player_id], "pit")

    return {"status": "pit updated"}

@app.put("/war")
def update_war(player_id: int, value: float, db: Session = Depends(get_db)):
    set_manual_war(db, player_id, value)
    return {"status": "updated"}

@app.get("/war")
def get_war(db: Session = Depends(get_db)):
    records = db.query(WarSnapshot).all()

    return [
        {
            "player_id": r.player_id,
            "date": r.date.isoformat() if r.date else None,
            "fwar_raw": r.fwar_raw,
            "fwar_manual": r.fwar_manual,
            "fwar_final": r.fwar_final
        }
        for r in records
    ]

# ---------------- PLAYER ----------------

@app.get("/players")
def get_players(db: Session = Depends(get_db)):
    return db.query(Player).all()

# ---------------- TEAM ----------------

@app.post("/teams")
def create_team(name: str, owner_name: str = None, db: Session = Depends(get_db)):
    team = Team(name=name, owner_name=owner_name)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team

@app.get("/teams")
def get_teams(db: Session = Depends(get_db)):
    return db.query(Team).all()

# ---------------- TEAM PLAYERS ----------------

@app.post("/teams/{team_id:int}/players")
def add_player_to_team(team_id: int, player_id: int, name: str = None, db: Session = Depends(get_db)):
    player = db.query(Player).filter_by(player_id=player_id).first()

    if not player:
        player = Player(player_id=player_id, name=name or f"Player {player_id}")
        db.add(player)
        db.commit()

    exists = db.query(TeamPlayer).filter_by(team_id=team_id, player_id=player_id).first()
    if exists:
        return {"status": "already exists"}

    tp = TeamPlayer(team_id=team_id, player_id=player_id)
    db.add(tp)
    db.commit()

    return {"status": "added"}

@app.delete("/teams/{team_id:int}/players/{player_id}")
def remove_player_from_team(team_id: int, player_id: int, db: Session = Depends(get_db)):
    tp = db.query(TeamPlayer).filter_by(team_id=team_id, player_id=player_id).first()

    if not tp:
        return {"error": "not found"}

    db.delete(tp)
    db.commit()

    return {"status": "removed"}

@app.put("/teams/{team_id}/players/{player_id}")
def update_player_id(
    team_id: int,
    player_id: int,
    new_player_id: int,
    db: Session = Depends(get_db)
):
    # 紐付け取得
    tp = (
        db.query(TeamPlayer)
        .filter_by(team_id=team_id, player_id=player_id)
        .first()
    )

    if not tp:
        return {"error": "player not found in team"}

    # 重複チェック
    exists = (
        db.query(TeamPlayer)
        .filter_by(team_id=team_id, player_id=new_player_id)
        .first()
    )

    if exists:
        return {"error": "new player already exists in team"}

    # 元のPlayer（名前保持用）
    old_player = db.query(Player).filter_by(player_id=player_id).first()

    # 新IDのPlayer
    player = db.query(Player).filter_by(player_id=new_player_id).first()

    if not player:
        player = Player(
            player_id=new_player_id,
            name=old_player.name if old_player else f"Player {new_player_id}"
        )
        db.add(player)
        db.commit()

    # ★ ここは必ず実行する（重要）
    tp.player_id = new_player_id
    db.commit()

    return {"status": "updated"}

# ---------------- TEAM DETAIL ----------------

@app.get("/teams/{team_id:int}")
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter_by(id=team_id).first()

    players = (
        db.query(Player)
        .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
        .filter(TeamPlayer.team_id == team_id)
        .all()
    )

    result_players = []

    for p in players:
        war = (
            db.query(WarSnapshot)
            .filter_by(player_id=p.player_id)
            .order_by(WarSnapshot.date.desc())
            .first()
        )

        result_players.append({
            "player_id": p.player_id,
            "name": p.name,
            "fwar": war.fwar_final if war else None
        })

    return {
        "team_id": team.id,
        "team_name": team.name,
        "players": result_players
    }

# ---------------- HISTORY ----------------

@app.get("/teams/{team_id:int}/war-history")
def get_team_war_history(team_id: int, db: Session = Depends(get_db)):
    players = (
        db.query(Player)
        .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
        .filter(TeamPlayer.team_id == team_id)
        .all()
    )

    history = defaultdict(float)

    for p in players:
        records = db.query(WarSnapshot).filter_by(player_id=p.player_id).all()
        for r in records:
            if r.fwar_final:
                history[r.date.isoformat()] += r.fwar_final

    return [
        {"date": d, "total_war": history[d]}
        for d in sorted(history.keys())
    ]

# ---------------- WAR TABLE ----------------

@app.get("/teams/{team_id:int}/war-table")
def get_team_war_table(team_id: int, db: Session = Depends(get_db)):
    players = (
        db.query(Player)
        .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
        .filter(TeamPlayer.team_id == team_id)
        .all()
    )

    dates = set()
    player_data = {}

    for p in players:
        records = db.query(WarSnapshot).filter_by(player_id=p.player_id).all()
        player_data[p.player_id] = {}

        for r in records:
            date = r.date.isoformat()
            dates.add(date)
            player_data[p.player_id][date] = r.fwar_final

    sorted_dates = sorted(dates)

    result = []
    for p in players:
        result.append({
            "player_id": p.player_id,
            "name": p.name,
            "wars": [player_data[p.player_id].get(d) for d in sorted_dates]
        })

    return {
        "dates": sorted_dates,
        "players": result
    }

# ---------------- SUMMARY（★修正済） ----------------

@app.get("/teams-summary")
def get_teams_summary(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    result = []

    for team in teams:
        players = (
            db.query(Player)
            .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
            .filter(TeamPlayer.team_id == team.id)
            .all()
        )

        team_total = 0
        player_list = []

        for p in players:
            war = (
                db.query(WarSnapshot)
                .filter_by(player_id=p.player_id)
                .order_by(WarSnapshot.date.desc())
                .first()
            )

            value = war.fwar_final if war else 0
            team_total += value

            player_list.append({
                "name": p.name,
                "war": value
            })

        result.append({
            "team_name": team.name,
            "players": player_list,
            "total_war": team_total
        })

    return result

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)