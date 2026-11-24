"""HED (Hierarchical Event Descriptors) annotations of the event tables, written with ndx-hed."""

from ndx_hed import HedLabMetaData
from pynwb import NWBFile

HED_SCHEMA_VERSION = "8.5.0"

VISUAL_STIMULUS_HED = "Sensory-event, Experimental-stimulus, Visual-presentation"
AIRPUFF_HED = "Sensory-event, Experimental-stimulus, Tactile-presentation, (Tactile-pressure, Torso-back)"
WHEEL_ACTIVATION_HED = "Agent-action, (Animal-agent, Run)"


def add_hed_schema(nwbfile: NWBFile) -> None:
    """Add the HedLabMetaData that names the HED schema version of the file's HED columns, once per file."""
    if "hed_schema" not in nwbfile.lab_meta_data:
        nwbfile.add_lab_meta_data(HedLabMetaData(hed_schema_version=HED_SCHEMA_VERSION))
