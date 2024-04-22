"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
import os
from benisty_2022_convert_session import session_to_nwb



# Parameters for conversion
root_path = Path("/media/amtra/Samsung_T5/CN_data")
data_dir_path = root_path / "Higley-CN-data-share"
output_dir_path = root_path / "Higley-conversion_nwb/"

session_ids = os.listdir(data_dir_path)
stub_test = True

session_ids = ['11222019_grabAM06_vis_stim', '11232019_grabAM07_vis_stim', '11232019_grabAM08_vis_stim']
for session_id in session_ids:
    session_folder = data_dir_path / Path(session_id)
    if os.path.isdir(session_folder):
        session_to_nwb(
            folder_path=session_folder,
            output_dir_path=output_dir_path,
            session_id=session_id,
            stub_test=stub_test,
        )
