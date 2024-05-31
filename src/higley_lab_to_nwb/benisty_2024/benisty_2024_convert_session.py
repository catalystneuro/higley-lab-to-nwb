"""Primary script to run to convert an entire session for of data using the NWBConverter."""

from pathlib import Path
from typing import Union
from neuroconv.utils import load_dict_from_file, dict_deep_update
from higley_lab_to_nwb.benisty_2024 import Benisty2024NWBConverter
import os


def _get_sampling_frequency_and_image_size(folder_path: Union[str, Path]):
    from roiextractors.extractors.tiffimagingextractors.scanimagetiff_utils import (
        extract_extra_metadata,
        parse_metadata,
        _get_scanimage_reader,
    )
    from natsort import natsorted

    file_paths = natsorted(Path(folder_path).glob("*.tif"))
    file_path = file_paths[0]
    image_metadata = extract_extra_metadata(file_path=file_path)
    parsed_metadata = parse_metadata(metadata=image_metadata)
    ScanImageTiffReader = _get_scanimage_reader()
    with ScanImageTiffReader(str(file_path)) as io:
        shape = io.shape()  # [frames, rows, columns]
    if len(shape) == 3:
        _num_frames, _num_rows, _num_columns = shape
    image_size = [_num_rows, _num_columns]
    return parsed_metadata["sampling_frequency"], image_size


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

    # Add 2p Imaging
    imaging_path = folder_path / "tiff"
    source_data.update(dict(TwoPhotonImaging=dict(folder_path=str(imaging_path), file_pattern="*.tif")))
    conversion_options.update(dict(TwoPhotonImaging=dict(stub_test=stub_test)))

    # Add suite2p Segmentation
    suite2p_path = folder_path / "suite2p"
    source_data.update(
        dict(Suite2pSegmentation=dict(folder_path=suite2p_path, plane_segmentation_name="Suite2pPlaneSegmentation"))
    )
    conversion_options.update(dict(Suite2pSegmentation=dict(stub_test=stub_test)))

    # Add CIDAN Segmentation
    cidan_path = folder_path / "CIDAN"
    parameters_file_path = cidan_path / "parameters.json"
    roi_list_file_path = cidan_path / "roi_list.json"
    mat_file_path = cidan_path / "timetraces.mat"
    plane_segmentation_name = "CIDANPlaneSegmentation"

    sampling_frequency, image_size = _get_sampling_frequency_and_image_size(folder_path=imaging_path)
    source_data.update(
        dict(
            CIDANSegmentation=dict(
                parameters_file_path=parameters_file_path,
                roi_list_file_path=roi_list_file_path,
                mat_file_path=mat_file_path,
                sampling_frequency=sampling_frequency,
                image_size=image_size,
                plane_segmentation_name=plane_segmentation_name,
            )
        )
    )
    conversion_options.update(
        dict(
            CIDANSegmentation=dict(
                include_roi_acceptance=False,
                plane_segmentation_name=plane_segmentation_name,
                stub_test=stub_test,
            )
        )
    )

    # Add ophys metadata
    ophys_metadata_path = Path(__file__).parent / "metadata" / "benisty_2024_ophys_metadata.yaml"
    ophys_metadata = load_dict_from_file(ophys_metadata_path)

    converter = Benisty2024NWBConverter(source_data=source_data, ophys_metadata=ophys_metadata)

    # Add datetime to conversion

    metadata = converter.get_metadata()
    subject_id = session_id.split("_")[1]
    metadata["Subject"].update(subject_id=subject_id)
    metadata["NWBFile"].update(session_id=session_id)

    # Update default metadata with the editable in the corresponding yaml file
    editable_metadata_path = Path(__file__).parent / "benisty_2024_metadata.yaml"
    editable_metadata = load_dict_from_file(editable_metadata_path)
    metadata = dict_deep_update(metadata, editable_metadata)

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
    session_ids = os.listdir(data_dir_path)
    session_id = "04072021_am2psi_05_spont"
    folder_path = data_dir_path / Path(session_id)
    session_to_nwb(
        folder_path=folder_path,
        output_dir_path=output_dir_path,
        session_id=session_id,
        stub_test=stub_test,
    )
