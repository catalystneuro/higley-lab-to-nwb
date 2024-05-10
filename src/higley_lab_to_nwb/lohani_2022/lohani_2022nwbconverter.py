"""Primary NWBConverter class for this dataset."""

from typing import Dict, List, Optional, Tuple, Union
from neuroconv import NWBConverter
from higley_lab_to_nwb.lohani_2022.interfaces.lohani_2022_spike2signals_interface import (
    Lohani2022Spike2SignalsInterface,
)
from higley_lab_to_nwb.lohani_2022.interfaces.lohani_2022_imaginginterface import Lohani2022MesoscopicImagingInterface

from neuroconv.datainterfaces import VideoInterface, FacemapInterface
from neuroconv.datainterfaces.ophys.tiff.tiffdatainterface import TiffImagingInterface


class Lohani2022NWBConverter(NWBConverter):
    """Primary conversion class."""

    data_interface_classes = dict(
        Spike2Signals=Lohani2022Spike2SignalsInterface,
        Video=VideoInterface,
        FacemapInterface=FacemapInterface,
    )

    def __init__(
        self,
        excitation_types: List[str],
        channels: List[str],
        source_data: Dict[str, dict],
        verbose: bool = True,
    ):
        self.excitation_types = excitation_types
        self.channels = channels
        for excitation_type in excitation_types:
            for channel in channels:
                suffix = f"{excitation_type}Excitation{channel}Channel"
                interface_name = f"Imaging{suffix}"
                self.data_interface_classes[interface_name]=Lohani2022MesoscopicImagingInterface
                
        self.verbose = verbose
        self._validate_source_data(source_data=source_data, verbose=self.verbose)

        self.data_interface_objects = {
            name: data_interface(**source_data[name])
            for name, data_interface in self.data_interface_classes.items()
            if name in source_data
        }

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
        facemap_interface = self.data_interface_objects["FacemapInterface"]
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
        facemap_interface.set_aligned_starting_time(ttl_times[0])
