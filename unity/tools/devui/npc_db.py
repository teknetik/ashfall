"""Persistent SQLite roster for the developer console's authored NPC voice assignments."""
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3

SEED = Path(__file__).with_name('npc_roster.json')
ID = re.compile(r'npc_[a-z0-9_]{2,60}$')
VOICE = re.compile(r'[A-Za-z0-9]{20}$')


def initialize(path):
    if path.is_symlink():
        raise ValueError('NPC database cannot be a symlink')
    source = json.loads(SEED.read_text())
    if source.get('schemaVersion') != 1 or not isinstance(source.get('npcs'), list):
        raise ValueError('Invalid NPC roster seed')
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('''CREATE TABLE IF NOT EXISTS npc_voice (
            npc_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            area TEXT NOT NULL,
            voice_id TEXT NOT NULL,
            voice_name TEXT NOT NULL,
            accent TEXT NOT NULL,
            line_count INTEGER NOT NULL CHECK (line_count >= 0)
        )''')
        for row in source['npcs']:
            if set(row) != {'id', 'name', 'area', 'voiceId', 'voiceName', 'accent', 'lineCount'} or not ID.fullmatch(row['id']) or not VOICE.fullmatch(row['voiceId']) or not all(isinstance(row[k], str) and 1 <= len(row[k]) <= 120 for k in ('name', 'area', 'voiceName', 'accent')) or type(row['lineCount']) is not int or row['lineCount'] < 0:
                raise ValueError('Invalid NPC roster row')
            db.execute('''INSERT INTO npc_voice(npc_id,name,area,voice_id,voice_name,accent,line_count)
                          VALUES(:id,:name,:area,:voiceId,:voiceName,:accent,:lineCount)
                          ON CONFLICT(npc_id) DO UPDATE SET name=excluded.name, area=excluded.area,
                          voice_id=excluded.voice_id, voice_name=excluded.voice_name,
                          accent=excluded.accent, line_count=excluded.line_count''', row)


def list_npcs(path):
    if path.is_symlink():
        raise ValueError('NPC database cannot be a symlink')
    with closing(sqlite3.connect(path)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute('''SELECT npc_id AS id, name, area, voice_id AS voiceId,
                            voice_name AS voiceName, accent, line_count AS lineCount
                            FROM npc_voice ORDER BY area, name''').fetchall()
    return [dict(row) for row in rows]
