import tifffile
from natsort import natsorted
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

def read_session_start_time(folder_path):
    tiff_file_paths = natsorted(folder_path.glob("*.tif"))
    with tifffile.TiffFile(tiff_file_paths[0]) as tif:
        metadata = tif.pages[0].tags['ImageDescription'].value

    lines = metadata.split('\r\n')
    date_time_str = lines[1]
    # Assuming the timezone is always 'Eastern Standard Time'
    date_time_obj = datetime.strptime(date_time_str[:-len(' Eastern Standard Time')], '%a, %d %b %Y %H:%M:%S')
    date_time_obj = date_time_obj.replace(tzinfo=ZoneInfo('US/Eastern'))
    
    return date_time_obj

def get_tiff_file_paths_sorted_by_channel(folder_path: str, start_frame_index: int = 0, stub_test: bool = False):

    tiff_file_paths = natsorted(folder_path.glob("*.tif"))
    if stub_test:
        tiff_file_paths = tiff_file_paths[:100]  # for testing
    selected_tiff_file_paths = tiff_file_paths[start_frame_index::3]

    return selected_tiff_file_paths


def create_tiff_stack(folder_path: str, output_file_path: str, start_frame_index: int = 0, frame_side: str = "left", stub_test: bool = False):
    
    selected_tiff_file_paths = get_tiff_file_paths_sorted_by_channel(
        folder_path=folder_path, start_frame_index=start_frame_index, stub_test = stub_test
    )
    frames = [tifffile.imread(file_path) for file_path in selected_tiff_file_paths]

    if frame_side == "left":
        stack = np.stack([frame[:, :512].transpose(1,0) for frame in frames], axis=0)
    elif frame_side == "right":
        stack = np.stack([frame[:, 512:].transpose(1,0)  for frame in frames], axis=0)
    else:
        raise ValueError("frame_side must be either 'right' or 'left'")

    tifffile.imwrite(output_file_path, stack)

    return 