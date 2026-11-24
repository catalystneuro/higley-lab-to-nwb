"""Convert every Lohani 2022 session, then run NWB Inspector on the output."""

from pathlib import Path

from nwbinspector import format_messages, inspect_all, save_report

from higley_lab_to_nwb.lohani_2022.lohani_2022_convert_session import session_to_nwb

root_path = Path("F:")
data_dir_path = root_path / "Higley-CN-data-share"
output_dir_path = root_path / "Higley-conversion_nwb"
allen_parcels_file_path = data_dir_path / "parcells_updated121519.mat"
stub_test = False
verbose = True

raw_data_dir_path = data_dir_path / "Lohani22 Meso Data"
for folder_path in sorted(path for path in raw_data_dir_path.iterdir() if path.is_dir()):
    session_id = folder_path.name
    _, subject_id, _ = session_id.split("_", 2)
    if verbose:
        print("-" * 80)
        print(f"Converting session {session_id}")
    session_to_nwb(
        folder_path=folder_path,
        parcellation_folder_path=data_dir_path
        / "Lohani22 Parcellated data"
        / subject_id.replace("AM", "")
        / "imaging with 575 excitation"
        / session_id,
        output_dir_path=output_dir_path,
        session_id=session_id,
        allen_parcels_file_path=allen_parcels_file_path,
        stub_test=stub_test,
        verbose=verbose,
    )

nwb_dir_path = output_dir_path / "nwb_stub" if stub_test else output_dir_path
results = list(inspect_all(path=nwb_dir_path))
save_report(
    report_file_path=nwb_dir_path / "inspector_result.txt",
    formatted_messages=format_messages(results, levels=["importance", "file_path"]),
    overwrite=True,
)
