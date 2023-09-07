from typing import Any

import aiosqlite


class DBExceptionError(RuntimeError):
    """An SQLite DB error occured."""


class DB(object):
    def __init__(self):
        self.conn: aiosqlite.Connection

    @classmethod
    async def create(cls, db_path: str):
        self = cls()
        try:
            self.conn = await aiosqlite.connect(db_path)
        except Exception as exc:
            raise DBExceptionError(exc) from exc
        else:
            await self.create_table()
        return self

    async def create_table(self) -> None:
        sql = "CREATE TABLE IF NOT EXISTS torrent (uid VARCHAR, torrent_id VARCHAR, complete BOOLEAN)"
        try:
            await self.conn.execute(sql)
        except Exception as exc:
            await self.conn.rollback()
            raise DBExceptionError(exc) from exc
        else:
            await self.conn.commit()

    async def add_torrent(self, uid, torrent_id: str) -> None:
        sql = "INSERT INTO torrent (uid, torrent_id, complete) VALUES (?,?,0)"
        try:
            await self.conn.execute(sql, (uid, torrent_id))
        except Exception as exc:
            await self.conn.rollback()
            raise DBExceptionError(exc) from exc
        else:
            await self.conn.commit()

    async def list_uncomplete_torrents(self) -> Any:
        sql = "SELECT * FROM torrent WHERE complete=0"
        try:
            cursor = await self.conn.execute(sql)
            data = await cursor.fetchall()
            await cursor.close()
        except Exception as exc:
            raise DBExceptionError(exc) from exc
        else:
            return data

    async def get_torrent_by_uid(self, uid: str) -> Any:
        sql = "SELECT * FROM torrent WHERE uid = ?"
        try:
            cursor = await self.conn.execute(sql, (uid,))
            data = await cursor.fetchall()
            await cursor.close()
        except Exception as exc:
            raise DBExceptionError(exc) from exc
        else:
            return data

    async def complete_torrent(self, torrent_id: str) -> None:
        sql = "UPDATE torrent SET complete=1 WHERE torrent_id = ?"
        try:
            await self.conn.execute(sql, (torrent_id,))
        except Exception as exc:
            await self.conn.rollback()
            raise DBExceptionError(exc) from exc
        else:
            await self.conn.commit()

    async def remove_torrent_by_id(self, torrent_id: str) -> None:
        sql = "DELETE FROM torrent WHERE torrent_id = ?"
        try:
            await self.conn.execute(sql, (torrent_id,))
        except Exception as exc:
            await self.conn.rollback()
            raise DBExceptionError(exc) from exc
        else:
            await self.conn.commit()
            await self.vacuum_db()

    async def vacuum_db(self) -> None:
        try:
            await self.conn.execute("VACUUM")
        except Exception as exc:
            raise DBExceptionError(exc) from exc

    async def close(self) -> None:
        try:
            await self.conn.close()
        except Exception as exc:
            raise DBExceptionError(exc) from exc
