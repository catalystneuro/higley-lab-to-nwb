import tifffile
from natsort import natsorted
import numpy as np

def get_tiff_file_paths_sorted_by_channel(folder_path: str, start_frame_index: int = 0):

    tiff_file_paths = natsorted(folder_path.glob("*.tif"))
    tiff_file_paths = tiff_file_paths[:28]  # for testing
    selected_tiff_file_paths = tiff_file_paths[start_frame_index::3]

    return selected_tiff_file_paths


def create_tiff_stack(folder_path: str, start_frame_index: int = 0, frame_side: str = "left"):

    output_file_path = str(folder_path) + f"_channel{start_frame_index}_{frame_side}.tiff"

    selected_tiff_file_paths = get_tiff_file_paths_sorted_by_channel(
        folder_path=folder_path, start_frame_index=start_frame_index
    )
    frames = [tifffile.imread(file_path) for file_path in selected_tiff_file_paths]

    if frame_side == "left":
        stack = np.stack([frame[:, :512] for frame in frames], axis=0)
    elif frame_side == "right":
        stack = np.stack([frame[:, 512:] for frame in frames], axis=0)
    else:
        raise ValueError("frame_side must be either 'right' or 'left'")

    tifffile.imwrite(output_file_path, stack, photometric="minisblack")

    return output_file_path

if __name__=="__main__":
    from pathlib import Path
    import matplotlib.pyplot as plt

    session_id = '11222019'
    subject_id = 'grabAM05'
    behaviour = 'vis_stim' # 'vis_stim' 'spont'
    folder_path = Path(f"/media/amtra/Samsung_T5/CN_data/Higley-CN-data-share/{session_id}_{subject_id}_{behaviour}")

    with tifffile.TiffFile(create_tiff_stack(folder_path)) as tif:
        image = tif.asarray()
        print(image.shape)
        for frame in image:
            plt.imshow(frame)
            plt.show()