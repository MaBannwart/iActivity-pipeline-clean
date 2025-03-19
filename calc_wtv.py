import sys
import numpy as np
import epoch as epoch
import pandas as pd

# Constants
WTV_EPOCH_TIME = 30 * 60  # 30 minutes
WTV_NUM_AXES = 3  # Triaxial data
# Non-wear if std-dev <3mg for at least 2 of the 3 axes
WTV_STD_CUTOFF = 0.003
WTV_STD_MIN_AXES = 2
# Non-wear if value range <50mg for at least 2 of the 3 axes
WTV_RANGE_CUTOFF = 0.050
WTV_RANGE_MIN_AXES = 2


def wear_time(merged_data, available_sensors):
    """
    Calculate the Wear-Time Validation (30-minute epochs) for a given sensor set.

    :param merged_data: merged sensor data
    :param available_sensors: list of available sensor locations
    :returns: ndarray of [time,worn], where worn is 0 (not worn), or 1 (worn) for each sensor location
    """
    # Wear-time epoch
    wtv_epoch_time = 30 * 60  # 30 minutes

    # Initialize temporary list to store wear-time data
    wear_time_data = pd.DataFrame()

    # Iterate over all available sensors
    for index, sensor_loc in enumerate(available_sensors):
        wt_log = calculate_wtv(merged_data[['Timestamps', sensor_loc + '__acc_x', sensor_loc + '__acc_y',
                                            sensor_loc + '__acc_z']].to_numpy(), np.timedelta64(wtv_epoch_time, 's'))
        if index == 0:
            wear_time_data['Timestamp'] = wt_log[:, 0]
        wear_time_data['WT_' + sensor_loc] = wt_log[:, 1]

    wear_time_data.set_index('Timestamp', inplace=True)
    wear_time_data.set_index(wear_time_data.index.round('1min'), inplace=True)
    wear_time_resampled = wear_time_data.resample('1min').ffill()

    # Extend the resampled wear time to match the recording end
    last_recorded_minute = merged_data['Timestamps'].iloc[-1].round('1min')  # get last recorded minute
    freq = wear_time_resampled.index.freq  # get frequency of the wear time dataframe
    interval_count = pd.date_range(start=wear_time_resampled.index[-1], end=last_recorded_minute,
                                   freq=freq).size - 1  # calculate the number of needed intervals

    # If there are missing timestamps
    if (interval_count > 0):
        # Calculate the missing timestamps
        new_timestamps = pd.date_range(start=wear_time_resampled.index[-1] + freq, periods=interval_count, freq=freq)
        # Create new dataframe with the rows needed for appending
        new_rows = pd.DataFrame([wear_time_resampled.iloc[-1]] * len(new_timestamps), index=new_timestamps)
        wear_time_resampled = pd.concat([wear_time_resampled, new_rows])

    wear_time_resampled.index.name = 'Timestamp'
    wear_time_resampled.reset_index(inplace=True)

    # Replace sequences which show less than 2 hours of consecutive wear or non-wear
    #wear_time_resampled.to_pickle("C:/Users/bannw/Documents/Axivity/pipeline-test/input/upload/temp_data.pkl")
    cleaned_wt = filter_transient_events(wear_time_resampled, available_sensors, min_length=90)

    return cleaned_wt


def filter_transient_events(event_data, available_sensors, min_length):
    """
    Smooth out non-consecutive events using the given minimum event length

    :param event_data: a column of events
    :param available_sensors: list of available sensor locations
    :param min_length: number of required consecutive events (in minutes)
    :returns: smoothed events with no event sequence shorter than the required length
    """

    # Create a copy of the data
    df = event_data.copy()
    # df.reset_index(inplace=True)

    # Iterate over all available sensors
    for index, sensor_loc in enumerate(available_sensors):
        # Get list with count of matching subsequent windows
        df['grouped'] = (df['WT_' + sensor_loc] != df['WT_' + sensor_loc].shift()).cumsum()

        # Count the number of consecutive windows with the same label
        group_sizes = df.groupby('grouped').size()

        # Iterate over all found sequences
        for group, size in enumerate(group_sizes):
            # Check if sequence is shorter than min_length
            if size < min_length:
                # Get indices of previous and next groups
                prev_group = group
                next_group = group + 2

                # Replace event sequence with previous event
                if prev_group in group_sizes and group_sizes[prev_group] >= min_length:
                    df.loc[df['grouped'] == group + 1, 'WT_' + sensor_loc] = \
                    df.loc[df['grouped'] == prev_group, 'WT_' + sensor_loc].iloc[0]
                elif next_group in group_sizes and group_sizes[next_group] >= min_length:
                    df.loc[df['grouped'] == group + 1, 'WT_' + sensor_loc] = \
                    df.loc[df['grouped'] == next_group, 'WT_' + sensor_loc].iloc[0]

        df.drop(columns='grouped')

    return df


def calculate_wtv(sample_values, epoch_time_interval=WTV_EPOCH_TIME, relative_to_time=None):
    """
    Calculate the Wear-Time Validation (30-minute epochs) for a given sample ndarray [[time_seconds, accel_x, accel_y, accel_z]].

    Based on the method by van Hees et al in PLos ONE 2011 6(7),
      "Estimation of Daily Energy Expenditure in Pregnant and Non-Pregnant Women Using a Wrist-Worn Tri-Axial Accelerometer".

    Accelerometer non-wear time is estimated from the standard deviation and range of each accelerometer axis,
    calculated for consecutive blocks of 30 minutes.
    A block was classified as non-wear time if the standard deviation was less than 3.0 mg
    (1 mg = 0.00981 m*s-2) for at least two out of the three axes,
    or if the value range, for at least two out of three axes, was less than 50 mg.

    :param epoch_time_interval: seconds per epoch (the algorithm is defined for 30 minutes)
    :param relative_to_time: None=align epochs to start of data, 0=align epochs to natural time, other=custom alignment
    :returns: ndarray of [time,worn], where worn is 0 (not worn), or 1 (worn)
    """

    if epoch_time_interval != WTV_EPOCH_TIME:
        print('WARNING: WTV algorithm is defined for %d seconds, but currently using %d seconds' % (
            WTV_EPOCH_TIME, epoch_time_interval), file=sys.stderr)

    # Split samples into epochs
    epochs = epoch.split_into_epochs(sample_values, epoch_time_interval, relative_to_time=relative_to_time)

    # Calculate each epoch
    num_epochs = len(epochs)
    result = np.empty((num_epochs, 2), dtype='O')
    for epoch_index in range(num_epochs):
        this_epoch = epochs[epoch_index]

        # Epoch start time and sample data
        epoch_time = this_epoch[0, 0]
        samples = this_epoch[:, 1:4].astype(float)

        # Per-axis/sample standard deviation and range
        stddev = np.std(samples, axis=0)
        value_range = np.ptp(samples, axis=0)

        # Count axes
        count_stddev_low = np.sum(stddev < WTV_STD_CUTOFF)
        count_range_low = np.sum(value_range < WTV_RANGE_CUTOFF)

        # Determine if worn
        if count_stddev_low >= WTV_STD_MIN_AXES or count_range_low >= WTV_RANGE_MIN_AXES:
            epoch_value = 0
        else:
            epoch_value = 1

        # Result
        result[epoch_index, 0] = epoch_time
        result[epoch_index, 1] = epoch_value

    return result
