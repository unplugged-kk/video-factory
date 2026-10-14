import datetime as dt
from contentos import storage


def test_jobs_land_in_a_per_day_folder_and_share_it(tmp_path):
    day = dt.datetime(2026, 10, 14, 9, tzinfo=dt.timezone.utc)
    a = storage.job_dir("video-a", now=day, jobs=tmp_path)
    b = storage.job_dir("video-b", now=day.replace(hour=20), jobs=tmp_path)
    assert a == tmp_path / "2026" / "10" / "14" / "video-a"
    assert b.parent == a.parent                          # same date, same folder
    assert storage.job_dir("video-a", now=day.replace(day=15), jobs=tmp_path) == a   # existing job is found, not duplicated


def test_old_month_layout_still_found_and_listed(tmp_path):
    old = tmp_path / "2026" / "10" / "old-job"
    old.mkdir(parents=True)
    new = storage.job_dir("new-job", now=dt.datetime(2026, 10, 14, tzinfo=dt.timezone.utc), jobs=tmp_path)
    assert storage.find_job_dir("old-job", tmp_path) == old
    assert storage.find_job_dir("new-job", tmp_path) == new
    assert {p.name for p in storage.iter_job_dirs(tmp_path)} == {"old-job", "new-job"}   # the '14' folder is not a job
