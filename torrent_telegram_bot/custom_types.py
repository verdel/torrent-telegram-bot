import datetime


class Torrent:
    def __init__(
        self,
        torrent_id: str,
        name: str,
        done_date: datetime.datetime | None,
        status: str,
        eta: datetime.timedelta | None,
        progress: float,
        download_speed: int,
        upload_speed: int,
        num_seeds_download: int,
        num_seeds_upload: int,
        ratio: float,
    ):
        self.torrent_id = torrent_id
        self.name = name
        self.done_date = done_date
        self.status = status
        self.eta = eta
        self.progress = progress
        self.download_speed = download_speed
        self.upload_speed = upload_speed
        self.num_seeds_download = num_seeds_download
        self.num_seeds_upload = num_seeds_upload
        self.ratio = ratio
