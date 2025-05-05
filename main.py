import os

import numpy as np
import pandas as pd
import shutil
import re

import calc_wtv
import get_activity_predictions
import get_gait_predictions
import merge_data
import ingest_data
import ENMO
import StepCount
from assemble_outcomes import assemble_data
import ActivityCounts
import utils.constants as constants
from collections import defaultdict
from pathlib import Path
from itertools import groupby
import utils.functions as utils
import time
import pickle


def group_func(filepath):
    """Return the first 2 substrings (split by underscore) of a filename from a filepath."""
    return filepath.name.split("_")[0] + "_" + filepath.name.split("_")[1]


def group_files(filepaths, key_function):
    """Return dictionary of sensor data belonging to a single recording (same FID and date)."""
    grp_files = defaultdict(list)
    data = sorted(filepaths, key=key_function)
    for key, group in groupby(data, key=key_function):
        grp_files[key] = list(group)
    return grp_files


def get_axivity_dictionary():
    """Return dictionary of sensor ids and sensor wear location."""
    sensor_dictionary = {
        "6021425": "WR", "6022402": "WL", "6023543": "AR", "6025696": "AL",  # 1
        "6024839": "WR", "6025973": "WL", "6026136": "AR", "6026358": "AL",  # 2
        "6024158": "WR", "6024254": "WL", "6024331": "AR", "6024795": "AL",  # 3
        "6022755": "AL", "6025826": "WL", "6026703": "AR", "6027821": "WR",  # 4
        "6021999": "AR", "6026668": "AL", "6026740": "WR", "6028005": "WL",  # 5
        "6026477": "WR", "6026622": "WL", "6026974": "AR", "6026988": "AL",  # 6
        "6021193": "WR", "6021826": "AR", "6021831": "AL", "6022846": "WL",  # 7
        "6019919": "WL", "6024741": "AR", "6026663": "WR", "6027898": "AL",  # 8
        "6023611": "AR", "6023660": "WL", "6024237": "AL", "6027302": "WR",  # 9
        "6021352": "AL", "6021581": "WL", "6021762": "WR", "6029064": "AR",  # 10
        "6024693": "WL", "6027437": "WR", "6028033": "AR", "6028146": "AL",  # 11
        "6021790": "AR", "6021888": "WL", "6027939": "AL", "6028120": "WR",  # 12
        "6021798": "AR", "6022928": "WL", "6022938": "AL", "6027474": "WR",  # 13
        "6021249": "AR", "6023911": "WL", "6024660": "WR", "6027877": "AL",  # 14
        "6021646": "AL", "6021696": "AR", "6022734": "WL", "6022750": "WR",  # 15
        "6021755": "WR", "6021240": "WL", "6021856": "AR", "6021640": "AL",  # 16
        "6020487": "WR", "6021793": "WL", "6021797": "AR", "6022158": "AL",  # 17
        "6022789": "WR", "6022915": "WL", "6027947": "AR", "6028043": "AL",  # 18
        "6021497": "WR", "6021589": "WL", "6021971": "AR", "6021038": "AL",  # 19
        "6024680": "WR", "6028118": "WL", "6028149": "AR", "6024945": "AL",  # 21
        "6022219": "WR", "6021586": "WL", "6021737": "AR", "6021572": "AL"   # 23
    }
    return sensor_dictionary


def main():
    start_time = time.time()

    # Get a list of uploaded cwa or wav files from the upload directory
    filelist = list(p.resolve() for p in Path(constants.ROOT).glob("*") if p.suffix in {".cwa", ".wav", ".zip"})

    # Get list of sensor ids and wear location
    axivity_list = get_axivity_dictionary()

    # Check for incomplete filenames
    for idx in range(len(filelist)):
        if "unknown" in filelist[idx].as_posix():
            print("Incomplete filename: " + filelist[idx].as_posix())
            try:
                sensor_id = filelist[idx].as_posix().split("_")[4]
                # Rename filename with correct wear location
                correct_filename = filelist[idx].as_posix().replace("unknown", axivity_list[sensor_id])
                filelist[idx].rename(correct_filename)
                # Replace list element
                filelist[idx] = Path(correct_filename)
            except:
                # Move file to error folder and remove from list
                shutil.move(filelist[idx].as_posix(), constants.ERROR)
                filelist.pop(idx)
                print("Incomplete file could not be renamed.")

    # Group cwa files by FID and date into a dictionary of separate recording sets
    recordings = group_files(filelist, group_func)

    # Check that only 4 sensor files are grouped together in a single set
    if all(len(data_set) > 4 for rec_key, data_set in recordings.items()):
        raise Exception("More than 4 sensor data files found for a single recording")

    # Iterate over all recordings
    for rec_key, data_set in recordings.items():
        print(f"Processing recording data {rec_key}")

        # For every measurement read in sensor data, synchronize and merge into a single dataframe
        print("Merging recorded sensor data")
        merged_data, available_sensors, meta_data = merge_data.assemble_sensor_data(data_set)

        # Get FID from filename
        fid = rec_key.split("_")[0][1:]
        # Check if fid is valid, else raise error
        if not (re.match('^\\d{7}$', fid)):
            raise Exception("FID not valid")

        # Get recording start date
        if 'Timestamps' in merged_data.columns:
            date_stamp = merged_data['Timestamps'].iloc[0].strftime('%Y%m%d%H%M%S')
        else:
            raise Exception("No timestamps found in merged data")

        # Get session ID from filename
        sid = data_set[0].as_posix().split("_")[-1]

        directory = constants.OUTPUT + "/" + fid + "/iactivity/" + date_stamp
        if not os.path.isdir(directory):
            os.makedirs(directory)
        # filename = directory + "/" + fid + "_merged.csv"
        fn_gait = directory + "/" + fid + "_gait.csv"
        fn_activity = directory + "/" + fid + "_activity.csv"
        fn_database = directory + "/" + fid + "_" + sid[:-4] + "_outcomes.csv"

        patient_details = utils.PatientDetails(fid, fid, date_stamp)

        # Debug Code: Save merged data to hard drive
        #merged_data.to_pickle("C:/Users/bannw/Documents/Axivity/pipeline-test/merged_test_data/merged_data.pkl")
        #pd.DataFrame({'available_sensors': available_sensors}).to_pickle(
        #    "C:/Users/bannw/Documents/Axivity/pipeline-test/merged_test_data/available_sensors.pkl")
        #pd.DataFrame({'meta_data': meta_data}).to_pickle(
        #    "C:/Users/bannw/Documents/Axivity/pipeline-test/merged_test_data/meta_data.pkl")
        #patient_data = pd.DataFrame(
        #    {'pid': [patient_details.pid], 'fid': [patient_details.fid], 'date_stamp': [patient_details.date_stamp]})
        #patient_data.to_pickle("C:/Users/bannw/Documents/Axivity/pipeline-test/merged_test_data/patient_data.pkl")

        # 1. Calculate wear-time
        print("Calculating wear-time")
        wear_time = calc_wtv.wear_time(merged_data, available_sensors)
        #wear_time = None

        # 2. Calculate counts
        print("Calculating activity counts")
        counts, patient_details = ActivityCounts.get_activity_counts(merged_data, available_sensors, patient_details)
        # counts = None

        # 3. Get the dominant wrist
        dominant_wrist = ActivityCounts.get_dominant_wrist(counts)

        # 4. Calculate activity durations
        print("Calculating activity durations")
        durations = ActivityCounts.get_activity_durations(counts)
        #durations = None

        # 5. Get activity levels
        print("Calculating activity levels")
        activity_levels = ENMO.get_activity_levels(merged_data, dominant_wrist)
        #activity_levels = None

        # 6. Get step count
        print("Calculating step count")
        if dominant_wrist == "wrist_l":
            wrist_file = next((filepath.as_posix() for filepath in data_set if "WL" in filepath.name), None)
        elif dominant_wrist == "wrist_r":
            wrist_file = next((filepath.as_posix() for filepath in data_set if "WR" in filepath.name), None)
        else:
            wrist_file = None
        # Use dominant wrist data to calculate step count
        step_count = StepCount.get_step_count(merged_data, wrist_file, dominant_wrist)

        # 7. Calculate gait/non-gait
        # print("Calculating gait predictions")
        # gait_predictions = get_gait_predictions.predict_gait(merged_data, fn_gait, available_sensors)
        gait_predictions = None

        # 8. Calculate activity classes
        # print("Calculating activity predictions")
        # activity_predictions = get_activity_predictions.predict_activity(merged_data, fn_activity, available_sensors)
        activity_predictions = None

        # 9. Calculate heart rate outcomes
        # TODO: Acquire 24/7 heart rate sensors to integrate into pipeline

        # 10. Assemble outcomes
        # Aggregate per minute
        counts = counts.groupby(np.arange(len(counts.index)) // 60).mean()  # avg count per minute
        durations_resampled = durations.groupby(
            np.arange(len(durations.index)) // 60).sum()  # nb of active seconds per minute
        # durations_resampled = None
        # activity_levels = None
        assemble_data(fn_database, merged_data, wear_time, counts, gait_predictions, activity_predictions,
                      durations_resampled, activity_levels, step_count)

        # Register data in database
        # TODO: Directly send data to database

        # Move processed raw data to archive
        # Get archive directory path
        archive = Path(constants.ARCHIVE)
        if not archive.is_dir():
            archive.mkdir()  # create directory if it does not exist

        # Iterate over all directories
        for raw_filepath in data_set:
            shutil.move(raw_filepath, archive)  # move already processed raw data files to archive

        # Upload outcome csv to server
        # ingest_data.main()

    execution_time = (time.time() - start_time)
    print('Execution time in seconds: ' + str(execution_time))


if __name__ == '__main__':
      main()
