"""
GlucoShield OhioT1DM Dataset Adapter
====================================
Modular adapter for parsing and loading OhioT1DM XML and CSV files.
Decoupled from hardcoded directory layouts and integrated with strict schema validation.
"""

import os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple

from activity_telemetry.dataset_adapter import BaseWearableAdapter
from activity_telemetry.ohio_schema import OhioT1DMConfig, OhioValidationReport
from activity_telemetry.ohio_data_validator import OhioDataValidator

class OhioT1DMAdapter(BaseWearableAdapter):
    """
    Adapter for OhioT1DM research datasets (2018 and 2020 releases).
    Parses native XML `<patient>` hierarchies and merges co-recorded streams.
    """
    def __init__(self, config: Optional[OhioT1DMConfig] = None):
        self.config = config or OhioT1DMConfig()
        self.validator = OhioDataValidator(self.config)

    @property
    def dataset_name(self) -> str:
        return "OhioT1DM"

    def list_participants(self, base_dir: str) -> List[str]:
        """Discovers all available OhioT1DM participant IDs across subdirectories."""
        if not os.path.exists(base_dir):
            return []

        participant_ids = set()
        for root, _, files in os.walk(base_dir):
            for f in files:
                if f.endswith(".xml") or f.endswith(".csv"):
                    # Participant ID is typically the leading 3 digits (e.g. 559-ws-training.xml -> 559)
                    base_name = os.path.splitext(f)[0]
                    parts = base_name.split("-")[0].split("_")[0]
                    if parts.isdigit() or len(parts) >= 3:
                        participant_ids.add(parts)

        return sorted(list(participant_ids))

    def load_participant_telemetry(
        self,
        participant_id: str,
        base_dir: str
    ) -> pd.DataFrame:
        """
        Loads all raw files for a given participant, parses XML/CSV,
        merges co-recorded streams, and returns standardized DataFrame.
        """
        if not os.path.exists(base_dir):
            raise FileNotFoundError(f"OhioT1DM directory does not exist: {base_dir}")

        matching_files = []
        for root, _, files in os.walk(base_dir):
            for f in files:
                if participant_id in f and (f.endswith(".xml") or f.endswith(".csv")):
                    matching_files.append(os.path.join(root, f))

        if not matching_files:
            raise FileNotFoundError(f"No telemetry files found for Ohio participant {participant_id} in {base_dir}")

        dfs = []
        for file_path in matching_files:
            if file_path.endswith(".xml"):
                df_part = self._parse_ohio_xml(file_path, participant_id)
            else:
                df_part = self._parse_ohio_csv(file_path, participant_id)
            if not df_part.empty:
                dfs.append(df_part)

        if not dfs:
            return pd.DataFrame(columns=["timestamp", "participant_id", "cgm_glucose", "heart_rate", "accel_mag", "steps", "bolus", "meal_carbs"])

        merged_df = pd.concat(dfs, ignore_index=True)
        merged_df = merged_df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        return merged_df

    def _parse_ohio_xml(self, xml_path: str, expected_pid: str) -> pd.DataFrame:
        """Parses native OhioT1DM XML patient document into a unified time series."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception as e:
            return pd.DataFrame()

        records_by_ts: Dict[str, Dict[str, Any]] = {}

        # 1. Glucose readings: <glucose_level ts="..." value="..."/>
        for el in root.findall(".//glucose_level"):
            ts = el.attrib.get("ts")
            val = el.attrib.get("value")
            if ts and val:
                rec = records_by_ts.setdefault(ts, {"timestamp": ts, "participant_id": expected_pid})
                try:
                    rec["cgm_glucose"] = float(val)
                except ValueError:
                    pass

        # 2. Heart rate: <heartrate ts="..." value="..."/>
        for el in root.findall(".//heartrate"):
            ts = el.attrib.get("ts")
            val = el.attrib.get("value")
            if ts and val:
                rec = records_by_ts.setdefault(ts, {"timestamp": ts, "participant_id": expected_pid})
                try:
                    rec["heart_rate"] = float(val)
                except ValueError:
                    pass

        # 3. Steps: <step ts="..." value="..."/>
        for el in root.findall(".//step"):
            ts = el.attrib.get("ts")
            val = el.attrib.get("value")
            if ts and val:
                rec = records_by_ts.setdefault(ts, {"timestamp": ts, "participant_id": expected_pid})
                try:
                    rec["steps"] = float(val)
                except ValueError:
                    pass

        # 4. Acceleration: <acceleration ts="..." value="..."/>
        for el in root.findall(".//acceleration"):
            ts = el.attrib.get("ts")
            val = el.attrib.get("value")
            if ts and val:
                rec = records_by_ts.setdefault(ts, {"timestamp": ts, "participant_id": expected_pid})
                try:
                    rec["accel_mag"] = float(val)
                except ValueError:
                    pass

        # 5. Bolus insulin: <bolus ts="..." dose="..."/>
        for el in root.findall(".//bolus"):
            ts = el.attrib.get("ts")
            val = el.attrib.get("dose") or el.attrib.get("value")
            if ts and val:
                rec = records_by_ts.setdefault(ts, {"timestamp": ts, "participant_id": expected_pid})
                try:
                    rec["bolus"] = float(val)
                except ValueError:
                    pass

        # 6. Meals: <meal ts="..." carbs="..."/>
        for el in root.findall(".//meal"):
            ts = el.attrib.get("ts")
            val = el.attrib.get("carbs") or el.attrib.get("value")
            if ts and val:
                rec = records_by_ts.setdefault(ts, {"timestamp": ts, "participant_id": expected_pid})
                try:
                    rec["meal_carbs"] = float(val)
                except ValueError:
                    pass

        if not records_by_ts:
            return pd.DataFrame()

        df = pd.DataFrame(list(records_by_ts.values()))
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp").reset_index(drop=True)

    def _parse_ohio_csv(self, csv_path: str, expected_pid: str) -> pd.DataFrame:
        """Parses CSV format if tabular files are provided."""
        try:
            df = pd.read_csv(csv_path)
        except Exception:
            return pd.DataFrame()

        ts_col = [c for c in df.columns if "time" in c.lower() or "date" in c.lower() or c == "ts"]
        if not ts_col:
            return pd.DataFrame()

        df["timestamp"] = pd.to_datetime(df[ts_col[0]])
        df["participant_id"] = expected_pid
        return df
