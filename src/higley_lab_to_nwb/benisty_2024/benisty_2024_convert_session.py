"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from neuroconv.utils import load_dict_from_file, dict_deep_update
from higley_lab_to_nwb.benisty_2024 import Benisty2024NWBConverter
import os
import glob


def session_to_nwb(
    folder_path: Union[str, Path], output_dir_path: Union[str, Path], session_id: str, stub_test: bool = False
):

    output_dir_path = Path(output_dir_path)
    if stub_test:
        output_dir_path = output_dir_path / "nwb_stub"
    output_dir_path.mkdir(parents=True, exist_ok=True)

    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    source_data = dict()
    conversion_options = dict()
    
    nwbfile_path = output_dir_path / f"{session_id}.nwb"

    source_data = dict()
    conversion_options = dict()

    # Add 2p Imaging
    folder_path = data_dir_path / session_id / "tiff"
    source_data.update(
        dict(TwoPhotonImagingGreenChannel=dict(folder_path=str(folder_path), file_pattern=f"*.tif", channel_name="Channel 1"))
    )
    conversion_options.update(dict(TwoPhotonImagingGreenChannel=dict(stub_test=stub_test)))
    # source_data.update(
    #     dict(TwoPhotonImagingRedChannel=dict(folder_path=str(folder_path), file_pattern=f"*.tif", channel_name="Channel 2"))
    # )
    # conversion_options.update(dict(TwoPhotonImagingRedChannel=dict(stub_test=stub_test, photon_series_index=1)))


    converter = Benisty2024NWBConverter(
        source_data=source_data,
    )

    # Add datetime to conversion
    metadata = converter.get_metadata()
    subject_id = session_id.split("_")[1]
    metadata["Subject"].update(subject_id=subject_id)
    metadata["NWBFile"].update(session_id=session_id)

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "benisty_2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

    # Add ophys metadata
    ophys_metadata_path = Path(__file__).parent / "metadata" / "benisty_2024_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)
    metadata = dict_deep_update(metadata, ophys_metadata)

    # Run conversion
    converter.run_conversion(
        metadata=metadata, nwbfile_path=nwbfile_path, conversion_options=conversion_options, overwrite=True
    )


if __name__ == "__main__":

    # Parameters for conversion
    root_path = Path("/media/amtra/Samsung_T5/CN_data")
    data_dir_path = root_path / "Higley-CN-data-share"
    output_dir_path = root_path / "Higley-conversion_nwb/"
    stub_test = True
    session_id = "04072021_am2psi_05_spont"
    folder_path = data_dir_path / Path(session_id)
    session_to_nwb(
        folder_path=folder_path,
        output_dir_path=output_dir_path,
        session_id=session_id,
        stub_test=stub_test,
    )
