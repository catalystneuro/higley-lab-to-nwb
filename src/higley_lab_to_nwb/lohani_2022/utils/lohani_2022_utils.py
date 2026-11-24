from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import tifffile
from natsort import natsorted
from pymatreader import read_mat


def read_session_start_time(folder_path: str | Path) -> datetime:
    """The acquisition time in the ImageDescription of the first TIFF of the session, in US/Eastern time."""
    tiff_file_paths = natsorted(Path(folder_path).glob("*.tif"))
    with tifffile.TiffFile(tiff_file_paths[0]) as tif:
        description = tif.pages[0].tags["ImageDescription"].value

    date_time_str = description.split("\r\n")[1]
    date_time = datetime.strptime(date_time_str[: -len(" Eastern Standard Time")], "%a, %d %b %Y %H:%M:%S")
    return date_time.replace(tzinfo=ZoneInfo("US/Eastern"))


def get_event_times_from_mat(file_path: str | Path, start_time_variable_name: str, end_time_variable_name: str):
    """Start and end times of an event from the `timing` struct of the lab's smrx_signals.mat."""
    mat = read_mat(str(file_path))
    if "timing" not in mat:
        raise ValueError(f"'timing' does not exist in {file_path}")
    timing = mat["timing"]
    for variable_name in (start_time_variable_name, end_time_variable_name):
        if variable_name not in timing:
            raise ValueError(f"'timing.{variable_name}' does not exist in {file_path}")
    return timing[start_time_variable_name], timing[end_time_variable_name]


def get_channel_trace_from_mat(file_path: str | Path, variable_name: str):
    """A trace from the `channels_data` struct of the lab's smrx_signals.mat, and its sampling frequency."""
    mat = read_mat(str(file_path))
    if "channels_data" not in mat:
        raise ValueError(f"'channels_data' does not exist in {file_path}")
    if variable_name not in mat["channels_data"]:
        raise ValueError(f"'channels_data.{variable_name}' does not exist in {file_path}")
    return mat["channels_data"][variable_name], float(mat["params"]["fsspike2"])
