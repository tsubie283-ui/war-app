from flask import Flask, jsonify, request
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import Team, TeamPlayer, Player, WarSnapshot
from crud import upsert_war, set_manual_war
from scraper import fetch_war_leaders_bat, fetch_war_leaders_pit
from collections import defaultdict
from flask import render_template
Base.metadata.create_all(bind=engine)

app = Flask(__name__)

# ---------------- DB ----------------

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# ---------------- WAR ----------------

@app.route("/fetch-war", methods=["POST"])
def fetch_war():
    db = SessionLocal()

    war_data = fetch_war_leaders_bat()

    print("=== BAT WAR KEYS ===")
    print(list(war_data.keys())[:20])

    players = db.query(Player).all()
    print("PLAYERS COUNT:", len(players))

    for p in players:
        if p.player_id in war_data:
            upsert_war(db, p.player_id, war_data[p.player_id], "bat")

    db.close()
    return jsonify({"status": "bat updated"})


@app.route("/fetch-war-pit", methods=["POST"])
def fetch_war_pit():
    db = SessionLocal()

    war_data = fetch_war_leaders_pit()

    print("=== PIT WAR KEYS ===")
    print(list(war_data.keys())[:20])

    players = db.query(Player).all()

    for p in players:
        if p.player_id in war_data:
            upsert_war(db, p.player_id, war_data[p.player_id], "pit")

    db.close()
    return jsonify({"status": "pit updated"})


@app.route("/war", methods=["GET"])
def get_war():
    db = SessionLocal()

    records = db.query(WarSnapshot).all()

    result = [
        {
            "player_id": r.player_id,
            "date": r.date.isoformat() if r.date else None,
            "fwar_raw": r.fwar_raw,
            "fwar_manual": r.fwar_manual,
            "fwar_final": r.fwar_final
        }
        for r in records
    ]

    db.close()
    return jsonify(result)


@app.route("/war", methods=["PUT"])
def update_war():
    data = request.get_json()

    player_id = data.get("player_id")
    value = data.get("value")

    db = SessionLocal()
    set_manual_war(db, player_id, value)
    db.close()

    return jsonify({"status": "updated"})

# ---------------- PLAYER ----------------

@app.route("/players", methods=["GET"])
def get_players():
    db = SessionLocal()
    players = db.query(Player).all()
    db.close()

    return jsonify([
        {"player_id": p.player_id, "name": p.name}
        for p in players
    ])

# ---------------- TEAM ----------------

@app.route("/teams", methods=["POST"])
def create_team():
    data = request.get_json()

    db = SessionLocal()
    team = Team(name=data["name"], owner_name=data.get("owner_name"))
    db.add(team)
    db.commit()
    db.refresh(team)
    db.close()

    return jsonify({"id": team.id, "name": team.name})


@app.route("/teams", methods=["GET"])
def get_teams():
    db = SessionLocal()
    teams = db.query(Team).all()
    db.close()

    return jsonify([
        {"id": t.id, "name": t.name}
        for t in teams
    ])

# ---------------- TEAM PLAYERS ----------------

@app.route("/teams/<int:team_id>/players", methods=["POST"])
def add_player(team_id):
    data = request.get_json()

    player_id = data["player_id"]
    name = data.get("name")

    db = SessionLocal()

    player = db.query(Player).filter_by(player_id=player_id).first()

    if not player:
        player = Player(player_id=player_id, name=name or f"Player {player_id}")
        db.add(player)
        db.commit()

    exists = db.query(TeamPlayer).filter_by(team_id=team_id, player_id=player_id).first()

    if exists:
        db.close()
        return jsonify({"status": "already exists"})

    tp = TeamPlayer(team_id=team_id, player_id=player_id)
    db.add(tp)
    db.commit()
    db.close()

    return jsonify({"status": "added"})


@app.route("/teams/<int:team_id>/players/<int:player_id>", methods=["DELETE"])
def remove_player(team_id, player_id):
    db = SessionLocal()

    tp = db.query(TeamPlayer).filter_by(team_id=team_id, player_id=player_id).first()

    if not tp:
        db.close()
        return jsonify({"error": "not found"})

    db.delete(tp)
    db.commit()
    db.close()

    return jsonify({"status": "removed"})

# ---------------- TEAM DETAIL ----------------

@app.route("/teams/<int:team_id>", methods=["GET"])
def get_team(team_id):
    db = SessionLocal()

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

    db.close()

    return jsonify({
        "team_id": team.id,
        "team_name": team.name,
        "players": result_players
    })

# ---------------- WAR HISTORY ----------------

@app.route("/teams/<int:team_id>/war-history", methods=["GET"])
def war_history(team_id):
    db = SessionLocal()

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

    db.close()

    return jsonify([
        {"date": d, "total_war": history[d]}
        for d in sorted(history.keys())
    ])

# ---------------- WAR TABLE ----------------

@app.route("/teams/<int:team_id>/war-table", methods=["GET"])
def war_table(team_id):
    db = SessionLocal()

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

    db.close()

    return jsonify({
        "dates": sorted_dates,
        "players": result
    })

# ---------------- SUMMARY ----------------

@app.route("/teams-summary", methods=["GET"])
def teams_summary():
    db = SessionLocal()

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

    db.close()

    return jsonify(result)

@app.route("/ui/teams")
def ui_teams():
    db = SessionLocal()

    teams = db.query(Team).all()

    result = []
    all_dates = set()
    histories = {}

    for team in teams:
        players = (
            db.query(Player)
            .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
            .filter(TeamPlayer.team_id == team.id)
            .all()
        )

        history = defaultdict(float)
        total = 0  # ★ Total WAR用

        for p in players:

            # -------------------------
            # 最新WAR（Total用）
            # -------------------------
            latest_war = (
                db.query(WarSnapshot)
                .filter_by(player_id=p.player_id)
                .order_by(WarSnapshot.date.desc())
                .first()
            )

            if latest_war and latest_war.fwar_final is not None:
                total += latest_war.fwar_final

            # -------------------------
            # 全履歴（Timeline用）
            # -------------------------
            records = (
                db.query(WarSnapshot)
                .filter_by(player_id=p.player_id)
                .all()
            )

            for r in records:
                if r.fwar_final is not None:
                    date = r.date.isoformat()
                    history[date] = round(history[date] + r.fwar_final, 3)
                    all_dates.add(date)

        histories[team.id] = history

        result.append({
            "id": team.id,
            "name": team.name,
            "total_war": round(total, 2)
        })

    db.close()

    return render_template(
        "teams.html",
        teams=result,
        dates=sorted(all_dates),
        histories=histories
    )

@app.route("/ui/teams/<int:team_id>")
def ui_team(team_id):
    db = SessionLocal()

    team = db.query(Team).filter_by(id=team_id).first()

    players = (
        db.query(Player)
        .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
        .filter(TeamPlayer.team_id == team_id)
        .all()
    )

    # -----------------------------
    # ① 最新WAR（上の表）
    # -----------------------------
    latest_players = []

    # -----------------------------
    # ② 日付収集（下の表の横軸）
    # -----------------------------
    all_dates = set()

    # player_id -> {date: war}
    matrix = {}

    for p in players:
        records = (
            db.query(WarSnapshot)
            .filter_by(player_id=p.player_id)
            .order_by(WarSnapshot.date.asc())
            .all()
        )

        player_map = {}
        latest = 0

        for r in records:
            date = r.date.isoformat()
            war = r.fwar_final or 0

            player_map[date] = war
            all_dates.add(date)

            latest = war  # 最後が最新

        matrix[p.name] = player_map

        latest_players.append({
            "name": p.name,
            "latest": latest
        })

    db.close()

    sorted_dates = sorted(all_dates)

    return render_template(
        "team.html",
        team=team,
        latest_players=latest_players,
        dates=sorted_dates,
        matrix=matrix
    )

@app.route("/ui/teams/<int:team_id>/players")
def ui_team_players(team_id):
    db = SessionLocal()

    team = db.query(Team).filter_by(id=team_id).first()

    players = (
        db.query(Player)
        .join(TeamPlayer, Player.player_id == TeamPlayer.player_id)
        .filter(TeamPlayer.team_id == team_id)
        .all()
    )

    result = []

    for p in players:
        records = (
            db.query(WarSnapshot)
            .filter_by(player_id=p.player_id)
            .order_by(WarSnapshot.date.asc())
            .all()
        )

        history = []
        for r in records:
            history.append({
                "date": r.date.isoformat(),
                "war": r.fwar_final or 0
            })

        result.append({
            "name": p.name,
            "history": history
        })

    db.close()

    return render_template("players.html", team=team, players=result)



@app.route("/fetch-war-all", methods=["POST"])
def fetch_war_all():
    db = SessionLocal()

    # BAT
    bat_data = fetch_war_leaders_bat()
    print("BAT FETCHED:", len(bat_data))

    players = db.query(Player).all()

    for p in players:
        if p.player_id in bat_data:
            upsert_war(db, p.player_id, bat_data[p.player_id], "bat")

    # PIT
    pit_data = fetch_war_leaders_pit()
    print("PIT FETCHED:", len(pit_data))

    for p in players:
        if p.player_id in pit_data:
            upsert_war(db, p.player_id, pit_data[p.player_id], "pit")

    db.close()

    return {"status": "bat + pit updated"}

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
