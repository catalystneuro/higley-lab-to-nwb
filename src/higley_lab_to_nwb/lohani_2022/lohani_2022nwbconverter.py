"""Primary NWBConverter class for this dataset."""

from typing import Dict, List
from pynwb import NWBFile
from neuroconv import NWBConverter
from neuroconv.datainterfaces import VideoInterface, FacemapInterface, TiffImagingInterface
from neuroconv.utils import DeepDict
from neuroconv.tools.nwb_helpers import make_or_load_nwbfile
from higley_lab_to_nwb.interfaces import (
    Spike2SignalsInterface,
    VisualStimulusInterface,
)


class Lohani2022NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        Spike2Signals=Spike2SignalsInterface,
        Video=VideoInterface,
        FacemapInterface=FacemapInterface,
        VisualStimulusInterface=VisualStimulusInterface,
    )

    def __init__(
        self,
        excitation_types: List[str],
        channels: List[str],
        source_data: Dict[str, dict],
        ophys_metadata: Dict[str, dict],
        verbose: bool = True,
    ):
        self.excitation_types = excitation_types
        self.channels = channels
        for excitation_type in excitation_types:
            for channel in channels:
                suffix = f"{excitation_type}Excitation{channel}Channel"
                interface_name = f"Imaging{suffix}"
                self.data_interface_classes[interface_name] = TiffImagingInterface

        self.verbose = verbose
        self._validate_source_data(source_data=source_data, verbose=self.verbose)

        self.data_interface_objects = {
            name: data_interface(**source_data[name])
            for name, data_interface in self.data_interface_classes.items()
            if name in source_data
        }

        self.ophys_metadata = ophys_metadata

    def get_metadata(self) -> DeepDict:
        metadata = super().get_metadata()

        metadata["Ophys"]["Device"] = self.ophys_metadata["Ophys"]["Device"]
        metadata["Ophys"]["OnePhotonSeries"] = self.ophys_metadata["Ophys"]["OnePhotonSeries"]
        metadata["Ophys"]["ImagingPlane"] = self.ophys_metadata["Ophys"]["ImagingPlane"]

        return metadata

    def run_conversion( # until [Issue #908](https://github.com/catalystneuro/neuroconv/issues/908) is fixed
        self,
        nwbfile_path: str  = None,
        nwbfile: NWBFile  = None,
        metadata: Dict  = None,
        overwrite: bool = False,
        conversion_options: Dict  = None,
    ) -> None:
        if metadata is None:
            metadata = self.get_metadata()

        self.validate_metadata(metadata=metadata)

        self.validate_conversion_options(conversion_options=conversion_options)

        self.temporally_align_data_interfaces()

        with make_or_load_nwbfile(
            nwbfile_path=nwbfile_path,
            nwbfile=nwbfile,
            metadata=metadata,
            overwrite=overwrite,
            verbose=self.verbose,
        ) as nwbfile_out:
            self.add_to_nwbfile(nwbfile_out, metadata, conversion_options)

        return

    def temporally_align_data_interfaces(self):
        ttlsignal_interface = self.data_interface_objects["Spike2Signals"]
        # Synch imaging
        for excitation_type in self.excitation_types:
            for channel in self.channels:
                imaging_interface = self.data_interface_objects[f"Imaging{excitation_type}Excitation{channel}Channel"]
                stream_id = next(
                    (
                        stream_id
                        for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                        if stream_name == f"TTLSignal{excitation_type}LED"
                    ),
                    None,
                )
                ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
                imaging_interface.set_aligned_starting_time(ttl_times[0])

        # Synch behaviour
        video_interface = self.data_interface_objects["Video"]
        video_interface._timestamps = video_interface.get_timestamps()
        stream_id = next(
            (
                stream_id
                for stream_id, stream_name in ttlsignal_interface.ttl_stream_ids_to_names_map.items()
                if stream_name == "TTLSignalPupilCamera"
            ),
            None,
        )
        ttl_times = ttlsignal_interface.get_event_times_from_ttl(stream_id=stream_id)
        video_interface.set_aligned_starting_time(ttl_times[0])

        if "FacemapInterface" in self.data_interface_objects.keys():
            facemap_interface = self.data_interface_objects["FacemapInterface"]
            facemap_interface.set_aligned_starting_time(ttl_times[0])
