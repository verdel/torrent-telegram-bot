# -*- coding: utf-8 -*-
from typing import Any

import transmissionrpc


class Transmission(object):
    def __init__(
        self,
        address: str = "localhost",
        port: int = 9091,
        user: str = "",
        password: str = "",
    ):
        self.address = address
        self.port = port
        self.user = user
        self.password = password
        self.tc = self.__get_client()

    def __get_client(self):
        return transmissionrpc.Client(self.address, self.port, self.user, self.password)

    def get_torrents(self) -> list[Any]:
        return self.tc.get_torrents()

    def get_torrent(self, torrent_id: str) -> Any:
        return self.tc.get_torrent(torrent_id)

    def remove_torrent(self, torrent_id: str, delete_data: bool = True):
        return self.tc.remove_torrent(ids=torrent_id, delete_data=delete_data)

    def add_torrent(self, torrent_data: str = "", **kwargs):
        if "download_dir" in kwargs:
            return self.tc.add_torrent(torrent=torrent_data, download_dir=kwargs.get("download_dir"))
        else:
            return self.tc.add_torrent(torrent=torrent_data)
