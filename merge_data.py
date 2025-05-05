import numpy as np
import pandas as pd
from openmovement.load import CwaData, MultiData
import utils.constants as constants


def get_meta_data(sensor_meta_data):
    """Generate structured meta data from sensor meta data."""
    # Initialize meta data dictionary with keys
    meta_data = dict(fid="_fid", gender="_gen", height="_hei", weight="_wei", age="_age", handedness="_han",
                     notes="_not", pathology="_pat", affected="_aff", betablockers="_bet", consent="_con",
                     location="_loc", setnr="_num")

    # Iterate over all meta_data parameters
    for param, key in zip(meta_data.keys(), meta_data.values()):
        # Check if meta data keys can be found in the sensor meta data
        if key in sensor_meta_data:
            meta_data[param] = sensor_meta_data[key]  # store data
            # TODO: Check if stored value is a valid meta data
        else:
            meta_data[param] = 'missing'  # store missing
    return meta_data


def assemble_sensor_data(filelist):
    """Assemble synchronized files into a single, merged file."""

    # Initialize temporary list to store sensor data
    sensor_data = list()
    # Initialize array to store sensor names
    available_sensors = []
    # Initialize array to store meta data
    set_meta_data = list()

    # Iterate over raw data files
    for filepath in filelist:
        with MultiData(filepath.as_posix(), verbose=False, include_gyro=True, include_temperature=False,
                     include_light=False) as raw_data:
            # As a pandas DataFrame
            samples = raw_data.get_samples()
            sampling_rate = raw_data.get_sample_rate()

            # 1. Get meta data
            if filepath.suffix == '.cwa' or filepath.suffix == ".zip":
                file_header = raw_data.inner_data.header
                # sampling_rate = file_header['sampleRate']
                gyro_range = file_header['gyroRange']
                accel_range = file_header['accelRange']
                meta_data_string = file_header['metadata']
            elif filepath.suffix == '.wav':
                info = raw_data.inner_data.info
                gyro_range = info['gyro_scale']
                accel_range = info['accel_scale']
                meta_data_single_string = info['recording']['Metadata']
                meta_data_string = dict(item.split("=") for item in meta_data_single_string.split("&"))
            else:
                raise Exception("Unhandled file extension " + filepath.suffix)


        # 2. Check for correct recording data
        # TODO: Read out cwa_data settings and check
        if {'time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z'}.issubset(samples.columns):
            if len(samples.columns) > 7:
                # Drop all columns apart from required columns
                samples = samples.loc[:, ['time', 'accel_x', 'accel_y', 'accel_z', 'gyro_x', 'gyro_y', 'gyro_z']]
            print("All required columns available")
        else:
            raise Exception("Raw data file is missing specific data columns. "
                            "Required are time, accel_x/y/z, and gyro_x/y/z.")

        if (sampling_rate == 50.0 and gyro_range == 1000.0) and accel_range == 8:
            print("Sensor settings ok.")
        else:
            print("Recording used wrong sensor settings.")
            print(f"Sampling rate: {sampling_rate}, accel range: {accel_range}, gyro range: {gyro_range}")
            # TODO: Adapt data for different sensor settings

        # Extract expected meta data from sensor meta data
        meta_data = get_meta_data(meta_data_string)
        # Store meta data foreach sensor
        set_meta_data.append(meta_data)
        # TODO: Check if sensor meta data is consistent apart from sensor location

        # 3. Check for large timestamp differences or other timestamp errors
        samples = samples.set_index('time')
        # Remove duplicate index values (these usually appear at the start and end of the series)
        #test = samples.index.duplicated(keep=False)
        samples = samples[~samples.index.duplicated(keep=False)]
        #TODO: Check how long the duplicate sequences are before deleting data

        # Calculate time differences between consecutive timestamps
        time_diffs = samples.index.to_series().diff().dt.total_seconds() * 1000  # Convert to milliseconds

        # Identify gaps that are larger than the expected interval (25 ms)
        #interval_ms = 30
        #large_gaps = time_diffs[time_diffs > interval_ms | (time_diffs < 0)].index

        #if len(large_gaps) > 0:
        #    # Warn about large gaps
        #    print(f"Warning: Large gaps detected in timestamps at indices {list(large_gaps)}.")
        #    print("Timestamps around these indices are not sequential.")

        # Find negative timestamp differences
        test = samples[samples.index.to_series().diff().lt(pd.Timedelta(0))].index
        # Remove the negative time frames
        if len(test) > 0:
            samples.drop(test, inplace=True)

        # Find timestamps outside of expectations
        test2 = samples[samples.index.to_series().gt(samples.index.to_series().iloc[0] + pd.Timedelta(days=8))].index
        if len(test2) > 0:
            samples.drop(test2, inplace=True)

        # Sampling frequency normally differs by around +152 microseconds (+/- 4 microseconds) (values from example file)
        result = samples.index.to_series().diff().gt(pd.Timedelta(milliseconds=25))
        if result.any():
            # Create dataframe with missing timestamp indices and timestamp differences
            ts_dif = pd.DataFrame(samples.index.to_series().diff()[np.where(result)[0]])
            # Report large timestamp differences to user
            print("There are large timestamp differences")
            print('Number of differences: {}'.format(len(ts_dif)))
            print('Max difference (s): {}'.format(ts_dif['time'].max().total_seconds()))
            print('Mean difference (s): {} +/- {}'.format(ts_dif['time'].mean().total_seconds(),
                                                          ts_dif['time'].std().total_seconds()))

            # Remove timestamps that are not between first and max timestamps (clock error)
            #samples_corr = samples.loc[samples.index[0]:samples.index.max()]
            #if not samples.equals(samples_corr):
            #    print('There were negative times between timestamps.\n'
            #          'Remove timestamps that do not continuously increase.')
            #    samples = samples_corr
            #    del samples_corr

            # TODO: Handle large timestamp differences
        else:
            print("No missing timestamps")

        # 4. Resample data to exactly 50 Hz
        if (samples.index.to_series().diff().value_counts()).size > 1:
            # Get old and new index
            old_idx = samples.index
            new_idx = pd.date_range(old_idx.min(), old_idx.max(), freq='20ms')
            resampled_data = samples.reindex(old_idx.union(new_idx)).interpolate('index').reindex(new_idx)
        else:
            resampled_data = samples

        # 5. Add pressure column with all entries set to 0.0
        resampled_data['Press'] = 0.0

        # 6. Correct sensor orientation and naming for ZurichMove algorithm
        # Extract sensor name from filename
        loc = filepath.as_posix().split("_")[-3]
        # Check if sensor location is valid
        if loc in constants.SENSOR_LOCATION:
            # Flip certain axes to match with ZurichMove (see transform_data)
            #if 'wrist' in constants.SENSOR_LOCATION[loc]:
            #    resampled_data.loc[:, ['accel_y', 'accel_x', 'gyro_y', 'gyro_x']] = resampled_data[
            #        ['accel_x', 'accel_y', 'gyro_x', 'gyro_y']].to_numpy()
            #    resampled_data.loc[:, ['accel_z', 'gyro_z']] *= -1
            #elif 'ankle' in constants.SENSOR_LOCATION[loc]:
            #    resampled_data.loc[:, ['accel_y', 'accel_z', 'gyro_y', 'gyro_z']] *= -1
            #else:
            #    raise Exception("No transformation defined for " + loc)

            # Rename sensor names for classification algorithms
            resampled_data.rename(columns={"accel_x": constants.SENSOR_LOCATION[loc] + "__acc_x",
                                           "accel_y": constants.SENSOR_LOCATION[loc] + "__acc_y",
                                           "accel_z": constants.SENSOR_LOCATION[loc] + "__acc_z",
                                           "gyro_x": constants.SENSOR_LOCATION[loc] + "__gyr_x",
                                           "gyro_y": constants.SENSOR_LOCATION[loc] + "__gyr_y",
                                           "gyro_z": constants.SENSOR_LOCATION[loc] + "__gyr_z",
                                           "Press": constants.SENSOR_LOCATION[loc] + "__press"},inplace=True)
                                           #"temperature": constants.SENSOR_LOCATION[loc] + "__temp",
                                           #"light": constants.SENSOR_LOCATION[loc] + "__light"}, inplace=True)

        else:
            raise Exception("Recording has invalid sensor location in filename")

        # Add sensor data to list
        sensor_data.append(resampled_data)
        available_sensors.append(constants.SENSOR_LOCATION[loc])
        # Remove unused data
        del result
        del resampled_data
        del samples
        del raw_data
        if 'new_idx' in locals(): del new_idx
        if 'old_idx' in locals(): del old_idx
        if 'ts_dif' in locals(): del ts_dif

    # 7. Align sensor data from different locations
    # TODO: Run alignment function to correct for sensor clock drift

    # 8. Merge data from different locations into a single dataframe
    merged_data = pd.DataFrame()
    if len(sensor_data) > 0:
        merged_data = sensor_data[0]
        for index in range(1, len(sensor_data)):
            merged_data = pd.merge_asof(merged_data, sensor_data[index],
                                        left_index=True, right_index=True,
                                        direction='nearest',
                                        tolerance=pd.Timedelta(19, 'milliseconds'))

        #count_nan_in_df = merged_data.isnull().sum().sum()
        # Remove unused data
        del sensor_data
        merged_data.dropna(inplace=True)
        merged_data.reset_index(inplace=True, names=['Timestamps'])

        # 9. Check if timestamps are continuous
        result = merged_data["Timestamps"].diff().gt(pd.Timedelta(milliseconds=20))
        if result.any():
            # Create dataframe with missing timestamp indices and timestamp differences
            merge_dif = pd.DataFrame(data={'differences': merged_data["Timestamps"].diff()[np.where(result)[0]]})
            # Report large timestamp differences to user
            print("There are large timestamp differences")
            print('Number of differences: {}'.format(len(merge_dif)))
            print('Max difference (s): {}'.format(merge_dif['differences'].max().total_seconds()))
            print('Mean difference (s): {} +/- {}'.format(merge_dif['differences'].mean().total_seconds(),
                                                          merge_dif['differences'].std().total_seconds()))
            # TODO: Handle large timestamp differences
        else:
            print("No missing timestamps")

    else:
        raise Exception("No sensor data available for merging")

    print("done")
    return merged_data, available_sensors, set_meta_data