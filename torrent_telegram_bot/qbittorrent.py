import secrets
import string
from datetime import datetime, timedelta
from time import sleep
from zoneinfo import ZoneInfo

from qbittorrentapi import Client

from torrent_telegram_bot.custom_types import Torrent


class Qbittorrent:
    """Simple torrent client class"""

    def __init__(
        self,
        address: str = "localhost",
        port: int = 8080,
        user: str = "",
        password: str = "",
    ):
        self.address = address
        self.port = port
        self.user = user
        self.password = password
        self.client = self.__get_client()

    def __get_client(self) -> Client:
        """Construct qbittorrent client instance"""
        return Client(host=self.address, port=self.port, username=self.user, password=self.password)

    def __generate_random_string(self, length):
        characters = string.ascii_letters + string.digits
        random_string = "".join(secrets.choice(characters) for i in range(length))
        return random_string

    def get_torrents(self) -> list[Torrent]:
        """Get all torrents from client"""
        torrents = self.client.torrents_info()
        return [
            Torrent(
                torrent_id=str(torrent.hash),
                name=torrent.name,
                done_date=datetime.fromtimestamp(
                    0 if torrent.completion_on < 0 else torrent.completion_on, ZoneInfo("UTC")
                ).replace(tzinfo=None),
                eta=timedelta(seconds=torrent.eta),
                status=torrent.state,
                progress=torrent.progress * 100,
                download_speed=torrent.dlspeed,
                upload_speed=torrent.upspeed,
                num_seeds_download=torrent.num_seeds + torrent.num_leechs,
                num_seeds_upload=torrent.num_seeds + torrent.num_leechs,
                ratio=torrent.ratio,
            )
            for torrent in torrents
        ]

    def get_torrent(self, torrent_id: str) -> Torrent | None:
        """Get torrent by torrent id"""
        torrents = self.client.torrents_info()
        for torrent in torrents:
            if torrent.hash == torrent_id:
                return Torrent(
                    torrent_id=str(torrent.hash),
                    name=torrent.name,
                    done_date=datetime.fromtimestamp(
                        0 if torrent.completion_on < 0 else torrent.completion_on, ZoneInfo("UTC")
                    ).replace(tzinfo=None),
                    eta=timedelta(seconds=torrent.eta),
                    status=torrent.state,
                    progress=torrent.progress * 100,
                    download_speed=torrent.dlspeed,
                    upload_speed=torrent.upspeed,
                    num_seeds_download=torrent.num_seeds + torrent.num_leechs,
                    num_seeds_upload=torrent.num_seeds + torrent.num_leechs,
                    ratio=torrent.ratio,
                )

    def remove_torrent(self, torrent_id: str, delete_data: bool = True):
        """Remove torrent by torrent hash"""
        return self.client.torrents_delete(torrent_hashes=torrent_id, delete_files=delete_data)

    def add_torrent(self, torrent_data: bytes, **kwargs) -> Torrent:
        """Add torrent to client"""
        temp_category = self.__generate_random_string(6)

        if "download_dir" in kwargs:
            result = self.client.torrents_add(
                torrent_files=torrent_data, save_path=kwargs.get("download_dir"), category=temp_category
            )
        else:
            result = self.client.torrents_add(torrent_files=torrent_data, category=temp_category)

        if result != "Ok.":
            raise Exception("Error adding torrent")

        while True:
            torrents = self.client.torrents_info(category=temp_category)
            if len(torrents) > 0:
                break
            else:
                sleep(1)

        torrent = torrents[0]

        self.client.torrents_remove_categories(categories=temp_category)

        return Torrent(
            torrent_id=str(torrent.hash),
            name=torrent.name,
            done_date=datetime.fromtimestamp(
                0 if torrent.completion_on < 0 else torrent.completion_on, ZoneInfo("UTC")
            ).replace(tzinfo=None),
            eta=timedelta(seconds=torrent.eta),
            status=torrent.state,
            progress=torrent.progress * 100,
            download_speed=torrent.dlspeed,
            upload_speed=torrent.upspeed,
            num_seeds_download=torrent.num_seeds + torrent.num_leechs,
            num_seeds_upload=torrent.num_seeds + torrent.num_leechs,
            ratio=torrent.ratio,
        )
