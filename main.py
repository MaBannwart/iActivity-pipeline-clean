import logging
import time
import re
import shutil
from pathlib import Path
from collections import defaultdict
from itertools import groupby
import numpy as np

# Internal imports
import utils.constants as constants
import utils.functions as utils
import merge_data
import ActivityCounts
import ENMO
import StepCount
import calc_wtv
from assemble_outcomes import assemble_data
import get_activity_predictions
import get_gait_predictions

logger = logging.getLogger(__name__)

def setup_environment():
    """Ensure all required directories exist."""
    for folder in [constants.INPUT_DIR, constants.OUTPUT_DIR, constants.ARCHIVE_DIR, constants.LOGS_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    log_file = constants.LOGS_DIR / "pipeline.log"
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

def get_recordings(filepath):
    """Finds and groups files."""
    # Get a list of raw .cwa, .wav or .zipped (.cwa/.raw) files from the input directory
    raw_files = [p for p in filepath.glob("*") if p.suffix in {".cwa", ".wav", ".zip"}]

    # Grouping logic
    def group_key(p): return "_".join(p.name.split("_")[:2])
    data = sorted(raw_files, key=group_key)
    return {k: list(g) for k, g in groupby(data, key=group_key)}

def process_recording(rec_key, data_set):
    """Processing part for a single patient recording."""
    logger.info(f"--- Processing: {rec_key} ---")
    
    # 1. Merge & Validate
    merged_data, available_sensors, meta_data = merge_data.assemble_sensor_data(data_set)  
   
    # Get FID from filename
    fid_match = re.search(r"\d{7}", rec_key)

    if not fid_match:
        raise ValueError(f"Invalid FID in {rec_key}")

    fid = fid_match.group()

    # Get recording start date
    date_stamp = merged_data['Timestamps'].iloc[0].strftime('%Y%m%d%H%M%S')
    # Get session ID from filename
    sid = data_set[0].stem.split("_")[-1] # stem removes extension
    
    # 2. Define Output Structure
    rec_dir = constants.OUTPUT_DIR / fid / "iactivity" / date_stamp
    rec_dir.mkdir(parents=True, exist_ok=True)
    
    outcome_path = rec_dir / f"{fid}_{sid}_outcomes.csv"

    # 3. Analytics Pipeline
    patient_details = utils.PatientDetails(fid, fid, date_stamp)
    
    wear_time = calc_wtv.wear_time(merged_data, available_sensors)
    counts, _ = ActivityCounts.get_activity_counts(merged_data, available_sensors, patient_details)
    dominant_wrist = ActivityCounts.get_dominant_wrist(counts)
    
    durations = ActivityCounts.get_activity_durations(counts)
    activity_levels = ENMO.get_activity_levels(merged_data, dominant_wrist)
    
    # Find the dominant wrist raw file
    loc_tag = "WL" if dominant_wrist == "wrist_l" else "WR"
    wrist_file = next((str(p) for p in data_set if f"_{loc_tag}_" in p.name), None)
    
    step_count = StepCount.get_step_count(merged_data, wrist_file, dominant_wrist)

    # gait_predictions = get_gait_predictions.predict_gait(merged_data, fn_gait, available_sensors)
    gait_predictions = None

    # activity_predictions = get_activity_predictions.predict_activity(merged_data, fn_activity, available_sensors)
    activity_predictions = None

    # TODO: Integrate continuous heart rate sensors into pipeline

    # 4. Aggregation
    counts_min = counts.groupby(np.arange(len(counts)) // 60).mean()
    durations_min = durations.groupby(np.arange(len(durations.index)) // 60).sum()

    if outcome_path.exists():
        logger.warning(f"Overwriting existing file: {outcome_path}")

    outcomes = assemble_data(
        outcome_path, merged_data, wear_time, counts_min, 
        gait_predictions, activity_predictions, durations_min, 
        activity_levels, step_count
    )
    
    return True

def main():
    setup_environment()
    start_time = time.time()

    recordings = get_recordings(constants.INPUT_DIR)

    # Group files by FID and date into a dictionary of separate patient recordings
    #recordings = group_files(raw_files, group_func)

    for rec_key, data_set in recordings.items():
        try:
            if len(data_set) > 4:
                logger.warning(f"Skipping {rec_key}: Too many sensors ({len(data_set)})")
                continue
                
            success = process_recording(rec_key, data_set)
            
            if success:
                for f in data_set:
                    shutil.move(str(f), constants.ARCHIVE_DIR / f.name)
                logger.info(f"Successfully archived {rec_key}")

        except Exception as e:
            logging.error(f"Failed to process {rec_key}: {e}", exc_info=True)

    logger.info(f"Total Execution Time: {time.time() - start_time:.2f}s")


if __name__ == '__main__':
      main()
