"""Converter for the Benisty 2024 sessions."""

from neuroconv import ConverterPipe

# Interface name -> the TTL channel whose first pulse is its first frame
FIRST_PULSE_ALIGNED_INTERFACES = dict(
    TwoPhotonImaging="TTLSignal2PExcitation",
    Suite2pSegmentation="TTLSignal2PExcitation",
    OnePhotonImaging="TTLSignalBlueLED",
    DffOnePhotonImaging="TTLSignalBlueLED",
    HemodynamicCorrectedOnePhotonImaging="TTLSignalBlueLED",
    OnePhotonImagingIsosbestic="TTLSignalVioletLED",
    DffOnePhotonImagingIsosbestic="TTLSignalVioletLED",
)


class Benisty2024NWBConverter(ConverterPipe):
    """The interfaces of one Benisty 2024 session, aligned to the Spike2 clock.

    The interfaces are named: "Spike2Signals", the keys of FIRST_PULSE_ALIGNED_INTERFACES, "CIDANSegmentation",
    "Video", "Facemap", "FacemapPython", "ProcessedWheelSignal" and "VisualStimulus". All but "Spike2Signals" are
    optional.
    """

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        interfaces = self.data_interface_objects
        spike2 = interfaces["Spike2Signals"]

        for name, channel_name in FIRST_PULSE_ALIGNED_INTERFACES.items():
            if name in interfaces:
                first_pulse_time = spike2.get_event_times_from_ttl_channel_name(channel_name=channel_name)[0]
                interfaces[name].temporal_alignment.move_earliest_observation_to(first_pulse_time)

        if "Video" in interfaces:
            first_pulse_time = spike2.get_event_times_from_ttl_channel_name(channel_name="TTLSignalPupilCamera")[0]
            interfaces["Video"].temporal_alignment.shift_times(first_pulse_time)

        # TODO align the FaceMap output to the video once the behavioral video is shared
