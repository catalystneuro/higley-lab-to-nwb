"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from parse import parse
from lohani_2022_convert_session import session_to_nwb

from nwbinspector import inspect_all
from nwbinspector.inspector_tools import save_report, format_messages

# Parameters for conversion
root_path = Path("F:")
data_dir_path = root_path / "Higley-CN-data-share"
output_dir_path = root_path / "Higley-conversion_nwb/"
stub_test = False
verbose = True

session_folder_format = "{date_string}_{subject_id}_{behavior_type}"

raw_imaging_dir_path = data_dir_path / "Lohani22 Meso Data"
for folder_path in raw_imaging_dir_path.iterdir():
    if folder_path.is_dir():
        session_id = folder_path.name
        metadata = parse(session_folder_format, session_id)
        if verbose:
            print("-" * 80)
            print(f"Converting session {session_id}")

        subject_id = metadata["subject_id"]
        parcellation_folder_path = (
            data_dir_path
            / "Lohani22 Parcellated data"
            / f"{subject_id.replace('AM', '')}"
            / "imaging with 575 excitation"
            / session_id
        )
        session_to_nwb(
            folder_path=folder_path,
            parcellation_folder_path=parcellation_folder_path,
            output_dir_path=output_dir_path,
            session_id=session_id,
            stub_test=stub_test,
            verbose=verbose,
        )

report_path = output_dir_path / "inspector_result.txt"
if not report_path.exists():
    results = list(inspect_all(path=output_dir_path))
    save_report(
        report_file_path=report_path,
        formatted_messages=format_messages(
            results,
            levels=["importance", "file_path"],
        ),
    )
