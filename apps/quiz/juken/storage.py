"""SQLite persistence shared by the CLI and future API."""

import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .quiz import Question, normalize


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, profile TEXT NOT NULL, level TEXT NOT NULL,
                planned INTEGER NOT NULL,
                started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                ended_at TEXT, status TEXT NOT NULL DEFAULT 'in_progress'
            );
            CREATE TABLE IF NOT EXISTS attempts (
                session_id TEXT NOT NULL REFERENCES sessions(id),
                position INTEGER NOT NULL, word TEXT NOT NULL,
                accepted_readings TEXT NOT NULL, answer TEXT NOT NULL,
                correct INTEGER NOT NULL CHECK(correct IN (0,1)),
                answered_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                PRIMARY KEY (session_id, position)
            );
            CREATE INDEX IF NOT EXISTS sessions_profile ON sessions(profile);
        """)

    def close(self):
        self.db.close()

    def start(self, profile: str, level: str, planned: int) -> str:
        session_id = str(uuid4())
        with self.db:
            self.db.execute("INSERT INTO sessions(id,profile,level,planned) VALUES(?,?,?,?)",
                            (session_id, profile, level, planned))
        return session_id

    def record(self, session_id: str, position: int, question: Question,
               answer: str, correct: bool):
        with self.db:
            self.db.execute("""INSERT INTO attempts
                (session_id,position,word,accepted_readings,answer,correct)
                VALUES(?,?,?,?,?,?)""", (session_id, position, question.word,
                    json.dumps(question.answers, ensure_ascii=False), normalize(answer), int(correct)))

    def finish(self, session_id: str, completed: bool):
        with self.db:
            self.db.execute("""UPDATE sessions SET
                ended_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),status=? WHERE id=?""",
                ("completed" if completed else "aborted", session_id))

    def answer_counts(self, profile: str) -> dict[str, tuple[int, int]]:
        """Per-word (correct, incorrect) totals, including interrupted sessions."""
        return {row["word"]: (row["correct"], row["incorrect"])
                for row in self.db.execute("""
                    SELECT a.word,SUM(a.correct) AS correct,SUM(1-a.correct) AS incorrect
                    FROM attempts a JOIN sessions s ON s.id=a.session_id
                    WHERE s.profile=? GROUP BY a.word""", (profile,))}

    def stats(self, profile: str) -> dict:
        summary = dict(self.db.execute("""SELECT COUNT(*) AS answered,
            COALESCE(SUM(a.correct),0) AS correct, COUNT(DISTINCT a.word) AS words
            FROM attempts a JOIN sessions s ON s.id=a.session_id WHERE s.profile=?""",
            (profile,)).fetchone())
        summary["sessions"] = self.db.execute(
            "SELECT COUNT(*) FROM sessions WHERE profile=?", (profile,)).fetchone()[0]
        summary["levels"] = [dict(row) for row in self.db.execute("""
            SELECT s.level,COUNT(*) AS answered,SUM(a.correct) AS correct
            FROM attempts a JOIN sessions s ON s.id=a.session_id WHERE s.profile=?
            GROUP BY s.level ORDER BY s.level""", (profile,))]
        summary["mistakes"] = [dict(row) for row in self.db.execute("""
            SELECT a.word,COUNT(*) AS answered,SUM(1-a.correct) AS mistakes
            FROM attempts a JOIN sessions s ON s.id=a.session_id WHERE s.profile=?
            GROUP BY a.word HAVING SUM(1-a.correct)>0
            ORDER BY mistakes DESC,a.word LIMIT 10""", (profile,))]
        return summary
