from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Candle, Direction, Signal, TradeStatus


class SignalStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def init(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    base_asset TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    entry_low REAL NOT NULL,
                    entry_high REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    tp1 REAL NOT NULL,
                    tp2 REAL NOT NULL,
                    tp3 REAL NOT NULL,
                    confidence INTEGER NOT NULL,
                    reasons TEXT NOT NULL,
                    news_summary TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    filled_at TEXT,
                    closed_at TEXT,
                    exit_price REAL,
                    pnl_r REAL DEFAULT 0,
                    exit_reason TEXT,
                    candles_waited INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_signals_symbol_status
                ON signals(symbol, status);
                """
            )

    def has_active_signal(self, symbol: str) -> bool:
        with self.connect() as db:
            row = db.execute(
                "SELECT 1 FROM signals WHERE symbol = ? AND status IN (?, ?) LIMIT 1",
                (symbol, TradeStatus.PENDING.value, TradeStatus.OPEN.value),
            ).fetchone()
            return row is not None

    def save_signal(self, signal: Signal) -> int:
        with self.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO signals (
                    symbol, base_asset, direction, timeframe, entry_low, entry_high,
                    stop_loss, tp1, tp2, tp3, confidence, reasons, news_summary,
                    created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    signal.symbol,
                    signal.base_asset,
                    signal.direction.value,
                    signal.timeframe,
                    signal.entry_low,
                    signal.entry_high,
                    signal.stop_loss,
                    signal.tp1,
                    signal.tp2,
                    signal.tp3,
                    signal.confidence,
                    "; ".join(signal.reasons),
                    signal.news_summary,
                    signal.created_at.isoformat(),
                    TradeStatus.PENDING.value,
                ),
            )
            return int(cursor.lastrowid)

    def update_with_candle(self, symbol: str, candle: Candle, expiry_candles: int = 2) -> None:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM signals WHERE symbol = ? AND status IN (?, ?)",
                (symbol, TradeStatus.PENDING.value, TradeStatus.OPEN.value),
            ).fetchall()
            for row in rows:
                self._update_row(db, row, candle, expiry_candles)

    def report(self) -> dict[str, float | int]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM signals WHERE status = ?", (TradeStatus.CLOSED.value,)).fetchall()
            total = len(rows)
            wins = len([row for row in rows if float(row["pnl_r"] or 0) > 0])
            pnl_values = [float(row["pnl_r"] or 0) for row in rows]
            return {
                "closed_trades": total,
                "win_rate": (wins / total) if total else 0,
                "average_r": (sum(pnl_values) / total) if total else 0,
                "total_r": sum(pnl_values),
                "open_or_pending": self._count_active(db),
            }

    def _update_row(
        self,
        db: sqlite3.Connection,
        row: sqlite3.Row,
        candle: Candle,
        expiry_candles: int,
    ) -> None:
        direction = Direction(row["direction"])
        status = TradeStatus(row["status"])
        if status == TradeStatus.PENDING:
            candles_waited = int(row["candles_waited"] or 0) + 1
            if candle.low <= row["entry_high"] and candle.high >= row["entry_low"]:
                db.execute(
                    "UPDATE signals SET status = ?, filled_at = ?, candles_waited = ? WHERE id = ?",
                    (TradeStatus.OPEN.value, candle.close_time.isoformat(), candles_waited, row["id"]),
                )
                status = TradeStatus.OPEN
            elif candles_waited > expiry_candles:
                db.execute(
                    "UPDATE signals SET status = ?, closed_at = ?, exit_reason = ?, candles_waited = ? WHERE id = ?",
                    (
                        TradeStatus.EXPIRED.value,
                        candle.close_time.isoformat(),
                        "Entry not touched within expiry window",
                        candles_waited,
                        row["id"],
                    ),
                )
                return
            else:
                db.execute(
                    "UPDATE signals SET candles_waited = ? WHERE id = ?",
                    (candles_waited, row["id"]),
                )
                return

        if status == TradeStatus.OPEN:
            exit_price, pnl_r, reason = evaluate_exit(row, direction, candle)
            if reason:
                db.execute(
                    """
                    UPDATE signals
                    SET status = ?, closed_at = ?, exit_price = ?, pnl_r = ?, exit_reason = ?
                    WHERE id = ?
                    """,
                    (
                        TradeStatus.CLOSED.value,
                        candle.close_time.isoformat(),
                        exit_price,
                        pnl_r,
                        reason,
                        row["id"],
                    ),
                )

    def _count_active(self, db: sqlite3.Connection) -> int:
        row = db.execute(
            "SELECT COUNT(*) AS count FROM signals WHERE status IN (?, ?)",
            (TradeStatus.PENDING.value, TradeStatus.OPEN.value),
        ).fetchone()
        return int(row["count"])


def evaluate_exit(row: sqlite3.Row, direction: Direction, candle: Candle) -> tuple[float | None, float, str | None]:
    entry = (float(row["entry_low"]) + float(row["entry_high"])) / 2
    stop = float(row["stop_loss"])
    risk = abs(entry - stop)
    if risk == 0:
        return None, 0, None

    if direction == Direction.LONG:
        if candle.low <= stop:
            return stop, -1.0, "SL hit"
        if candle.high >= float(row["tp3"]):
            return float(row["tp3"]), 3.0, "TP3 hit"
        if candle.high >= float(row["tp2"]):
            return float(row["tp2"]), 2.0, "TP2 hit"
        if candle.high >= float(row["tp1"]):
            return float(row["tp1"]), 1.0, "TP1 hit"
    else:
        if candle.high >= stop:
            return stop, -1.0, "SL hit"
        if candle.low <= float(row["tp3"]):
            return float(row["tp3"]), 3.0, "TP3 hit"
        if candle.low <= float(row["tp2"]):
            return float(row["tp2"]), 2.0, "TP2 hit"
        if candle.low <= float(row["tp1"]):
            return float(row["tp1"]), 1.0, "TP1 hit"
    return None, 0, None
