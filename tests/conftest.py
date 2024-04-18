import pytest


from utils.summary_downloader import SummaryDownloader


@pytest.fixture(scope='session')
def download_summaries(tmp_path_factory):

    temp_dir = tmp_path_factory.mktemp("dld_data")

    date = "Oct 12, 2016"
    sdl = SummaryDownloader(temp_dir, date, zip_summaries=False, cleanup=False)
    sdl.run()
    return sdl
