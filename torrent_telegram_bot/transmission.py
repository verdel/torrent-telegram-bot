from transmission_rpc import Client

from torrent_telegram_bot.custom_types import Torrent


class Transmission:
    """Simple torrent client class"""

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
        self.client = self.__get_client()

    def __get_client(self) -> Client:
        """Construct transmission client instance"""
        return Client(host=self.address, port=self.port, username=self.user, password=self.password)

    def get_torrents(self) -> list[Torrent]:
        """Get all torrents from client"""
        torrents = self.client.get_torrents()
        return [
            Torrent(
                torrent_id=str(torrent.id),
                name=torrent.name,
                done_date=torrent.done_date,
                eta=torrent.eta,
                status=torrent.status,
                progress=torrent.progress,
                download_speed=torrent.rate_download,
                upload_speed=torrent.rate_upload,
                num_seeds_download=torrent.peers_sending_to_us,
                num_seeds_upload=torrent.peers_getting_from_us,
                ratio=torrent.ratio,
            )
            for torrent in torrents
        ]

    def get_torrent(self, torrent_id: str) -> Torrent | None:
        """Get torrent by torrent id"""
        torrent = self.client.get_torrent(int(torrent_id))
        return Torrent(
            torrent_id=str(torrent.id),
            name=torrent.name,
            done_date=torrent.done_date,
            eta=torrent.eta,
            status=torrent.status,
            progress=torrent.progress,
            download_speed=torrent.rate_download,
            upload_speed=torrent.rate_upload,
            num_seeds_download=torrent.peers_sending_to_us,
            num_seeds_upload=torrent.peers_getting_from_us,
            ratio=torrent.ratio,
        )

    def remove_torrent(self, torrent_id: str, delete_data: bool = True):
        """Remove torrent by torrent id"""
        return self.client.remove_torrent(ids=int(torrent_id), delete_data=delete_data)

    def add_torrent(self, torrent_data: bytes, **kwargs) -> Torrent:
        """Add torrent to client"""
        if "download_dir" in kwargs:
            torrent = self.client.add_torrent(torrent=torrent_data, download_dir=kwargs.get("download_dir"))
        else:
            torrent = self.client.add_torrent(torrent=torrent_data)
        return Torrent(
            torrent_id=str(torrent.id),
            name=torrent.name,
            done_date=None,
            eta=None,
            status="",
            progress=0,
            download_speed=0,
            upload_speed=0,
            num_seeds_download=0,
            num_seeds_upload=0,
            ratio=0,
        )
