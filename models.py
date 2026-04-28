from sqlalchemy import Column, Integer, String, Float, Date, Boolean, UniqueConstraint, ForeignKey
from database import Base

class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, unique=True)
    name = Column(String)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    owner_name = Column(String, nullable=True)

class TeamPlayer(Base):
    __tablename__ = "team_players"
    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    player_id = Column(Integer, ForeignKey("players.player_id"))

class WarSnapshot(Base):
    __tablename__ = "war_snapshots"
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer)
    date = Column(Date)
    fwar_bat = Column(Float, default=0)
    fwar_pit = Column(Float, default=0)
    fwar_raw = Column(Float)
    fwar_manual = Column(Float, nullable=True)
    fwar_final = Column(Float)

    __table_args__ = (UniqueConstraint("player_id", "date"),)

class PlayerDailyStats(Base):
    __tablename__ = "player_daily_stats"
    player_id = Column(Integer, primary_key=True)
    date = Column(Date)
    is_dnp = Column(Boolean)

    pa = Column(Integer, nullable=True)
    hits = Column(Integer, nullable=True)
    doubles = Column(Integer, nullable=True)
    hr = Column(Integer, nullable=True)
    rbi = Column(Integer, nullable=True)
    strikeouts = Column(Integer, nullable=True)
    walks = Column(Integer, nullable=True)

    innings_pitched = Column(Float, nullable=True)
    earned_runs = Column(Integer, nullable=True)
    home_runs_allowed = Column(Integer, nullable=True)
    strikeouts_p = Column(Integer, nullable=True)
    walks_p = Column(Integer, nullable=True)