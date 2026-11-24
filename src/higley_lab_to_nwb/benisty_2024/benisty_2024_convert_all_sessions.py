"""Convert every Benisty 2024 2p-only session."""

from pathlib import Path

from higley_lab_to_nwb.benisty_2024.benisty_2024_convert_2p_only_session import session_to_nwb

root_path = Path("/media/amtra/Samsung_T5/CN_data")
data_dir_path = root_path / "Higley-CN-data-share"
output_dir_path = root_path / "Higley-conversion_nwb/"
stub_test = True

for session_folder in sorted(path for path in data_dir_path.iterdir() if path.is_dir()):
    session_to_nwb(
        folder_path=session_folder,
        output_dir_path=output_dir_path,
        session_id=session_folder.name,
        stub_test=stub_test,
    )
