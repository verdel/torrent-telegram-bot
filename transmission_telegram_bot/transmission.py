from transmission_rpc import Client, Torrent


class Transmission(object):
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
        self.tc = self.__get_client()

    def __get_client(self) -> Client:
        """Construct transmission client instance"""
        return Client(host=self.address, port=self.port, username=self.user, password=self.password)

    def get_torrents(self) -> list[Torrent]:
        """Get all torrents from transmission"""
        return self.tc.get_torrents()

    def get_torrent(self, torrent_id: int) -> Torrent:
        """Get torrent by torrent id"""
        return self.tc.get_torrent(torrent_id)

    def remove_torrent(self, torrent_id: int, delete_data: bool = True):
        """Remove torrent by torrent id"""
        return self.tc.remove_torrent(ids=torrent_id, delete_data=delete_data)

    def add_torrent(self, torrent_data: str = "", **kwargs) -> Torrent:
        """Add torrent to transmission"""
        if "download_dir" in kwargs:
            return self.tc.add_torrent(torrent=torrent_data, download_dir=kwargs.get("download_dir"))
        else:
            return self.tc.add_torrent(torrent=torrent_data)
