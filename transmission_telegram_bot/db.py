# -*- coding: utf-8 -*-
import sqlite3


class DBException(RuntimeError):
    """An SQLite DB error occured."""


class DB(object):
    def __init__(self, db_path):
        try:
            self.conn = sqlite3.connect(db_path)
            self.cur = self.conn.cursor()
        except Exception as exc:
            raise DBException(exc)
        else:
            self.create_table()

    def create_table(self):
        sql = 'CREATE TABLE IF NOT EXISTS torrent (uid VARCHAR, torrent_id VARCHAR, complete BOOLEAN)'
        try:
            self.cur.execute(sql)
        except Exception as exc:
            self.cur.rollback()
            raise DBException(exc)
        else:
            self.conn.commit()

    def add_torrent(self, uid, torrent_id):
        sql = 'INSERT INTO torrent (uid, torrent_id, complete) VALUES (?,?,0)'
        try:
            self.cur.execute(sql, (uid, torrent_id))
        except Exception as exc:
            self.conn.rollback()
            raise DBException(exc)
        else:
            self.conn.commit()

    def list_uncomplete_torrents(self):
        sql = 'SELECT * FROM torrent WHERE complete=0'
        try:
            data = self.cur.execute(sql).fetchall()
        except Exception as exc:
            raise DBException(exc)
        else:
            return data

    def get_torrent_by_uid(self, uid):
        sql = 'SELECT * FROM torrent WHERE uid = ?'
        try:
            data = self.cur.execute(sql, (uid,)).fetchall()
        except Exception as exc:
            raise DBException(exc)
        else:
            return data

    def complete_torrent(self, torrent_id):
        sql = 'UPDATE torrent SET complete=1 WHERE torrent_id = ?'
        try:
            self.cur.execute(sql, (torrent_id,))
        except Exception as exc:
            self.cur.rollback()
            raise DBException(exc)
        else:
            self.conn.commit()

    def remove_torrent_by_id(self, torrent_id):
        sql = 'DELETE FROM torrent WHERE torrent_id = ?'
        try:
            self.cur.execute(sql, (torrent_id,))
        except Exception as exc:
            self.cur.rollback()
            raise DBException(exc)
        else:
            self.conn.commit()
            self.vacuum_db()

    def vacuum_db(self):
        try:
            self.conn.execute('VACUUM')
        except Exception as exc:
            raise DBException(exc)
