from datetime import date
from sqlalchemy.orm import Session
from models import WarSnapshot

def upsert_war(db: Session, player_id: int, war_value: float, war_type: str):
    today = date.today()

    record = (
        db.query(WarSnapshot)
        .filter_by(player_id=player_id, date=today)
        .first()
    )

    if not record:
        record = WarSnapshot(
            player_id=player_id,
            date=today,
            fwar_bat=0,
            fwar_pit=0,
            fwar_final=0
        )
        db.add(record)

    # ★ タイプ別に保存
    if war_type == "bat":
        record.fwar_bat = war_value
    elif war_type == "pit":
        record.fwar_pit = war_value

    # ★ 合計
    total = (record.fwar_bat or 0) + (record.fwar_pit or 0)

    # manual優先
    record.fwar_final = (
        record.fwar_manual
        if record.fwar_manual is not None
        else total
    )

    db.commit()


def set_manual_war(db: Session, player_id: int, value: float):
    today = date.today()

    record = (
        db.query(WarSnapshot)
        .filter_by(player_id=player_id, date=today)
        .first()
    )

    if record:
        record.fwar_manual = value
        record.fwar_final = value
        db.commit()