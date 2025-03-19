import glob
from statistics import mode
from argparse import ArgumentParser
from utils.constants import *
from utils.data import get_data
from joblib import load
import pandas as pd
import numpy as np
import os
from pathlib import Path
from utils.utils import *
import matplotlib.pyplot as plt
import seaborn as sns


root = r'C:/Users/bannw/Documents/00_Cereneo/01_Projects/Anja/time_series_merged/'

def get_parser():
    # Parse input arguments
    parser = ArgumentParser()

    # CSV location
    parser.add_argument('file_path', type=str, help='CSV file to make predictions.')

    # Sensor positions
    parser.add_argument('-s', '--sensors', default='all', type=str, choices=VALID_SENSOR_POS_ACTIVITY,
                        help='Specify sensor positions to use')

    # Affected flag
    parser.add_argument('-a', '--affected', action='store_true',
                        help='Set this flag if side is affected. Can only be used in conjunction with "left"/"right" sensor setups.')

    # In person normalization flag
    parser.add_argument('-n', '--no_inperson_standardization', action='store_true',
                        help='Set this flag if inperson normalization should be shut off. This is recommended for scenarios where the data collection protocol deviated significantly from the paper. (E.g. longer timeseries, healthy patients, patients with non diverse activities like e.g. only lying)')

    # Output location
    parser.add_argument('-o', '--output_location', type=str, help='Specify output location.')

    # Append prediction
    parser.add_argument('--append', action='store_true',
                        help='Set this flag if output should be appended to input file.')

    return parser


def make_predictions(model_fn, data, task):
    model = load(model_fn)
    curr_preds = model.predict(data)
    curr_preds = np.array([PRED_TO_STRING[task][label] for label in curr_preds]).repeat(128)
    return curr_preds


def main(fn, fn_df, s_setup, out_loc, affected=False, no_inperson_standardization=False, data=None, append=False):
    # Get data from file
    if data is None:
        data = get_data(fn_df, s_setup, patient_standardization=not no_inperson_standardization)

    # Get predictions
    task = 'activity'
    predictions = {}
    if s_setup not in ['right', 'left']:
        model_fn = os.path.join('models', task,
                                f'{s_setup}{"_no_in_person_standardized" if no_inperson_standardization else ""}.joblib')
    else:
        # For unilateral setup, use not_affected by default and affected if configured by user
        if affected:
            setup = 'affected'
        else:
            setup = 'not_affected'
        model_fn = os.path.join('models', task,
                                f'{setup}{"_no_in_person_standardized" if no_inperson_standardization else ""}.joblib')
    predictions[f'{task}_prediction'] = make_predictions(model_fn, data, task)

    if not append:
        if out_loc is None:
            out_loc = Path(fn).parent.absolute()

        # Save predictions
        df = pd.DataFrame.from_dict(predictions)
        # Calculate pruned data length
        num_windows = len(fn_df.index) // 128
        data_length = num_windows * 128
        df.insert(0, 'Time', fn_df.loc[:data_length, ['Timestamps']])
        Path(out_loc).mkdir(exist_ok=True, parents=True)

        # Swap prediction values
        # df['gait_prediction'] = df['gait_prediction'].map({'gait': 'no-gait', 'no-gait': 'gait'})

        # Filter out transient predictions
        predictions_filtered = filter_transient_predictions(df['activity_prediction'], 2)
        # Add filtered predictions to dataframe
        df['filtered_prediction'] = np.repeat(predictions_filtered, 128)

        df.set_index('Time', inplace=True)
        df_resampled = df.resample('1min').apply(lambda x: mode(x))
        df_resampled.reset_index(level=0, inplace=True)

        #df_resampled.to_csv(fn, index=False)

        print(f"Finished computing activity detections: {fn}.")

        ## Plot data
        # [head, ts_filename] = os.path.split(fn)
        # date_string = 'Test date'
        # fig_string = 'Test figure'
        # fig = plot_figure(df, fig_string)
        # fig.savefig(head + "/" + fig_string + '_' + date_string + '_activity_predictions.png')

        return df_resampled
    else:
        # Save predictions
        try:
            # df = pd.read_csv(fn)
            print("Nothing happening here")
        except pd.errors.ParserError as e:
            log(f"{fn} contains bad lines, those lines will be skipped and deleted.")
            df = pd.read_csv(fn, on_bad_lines='skip')
        if df.isnull().values.any():
            log(f"{fn} contains invalid values on lines {np.argwhere(df.isnull().values)[:, 0]}.")
        df = df.dropna()
        df = pd.concat((df, pd.DataFrame.from_dict(predictions)), axis=1)
        df.to_csv(fn, index=False)


def filter_transient_predictions(predictions, filter_length):
    # Reduce data to a single prediction per window (128)
    predictions_filtered = predictions.iloc[::128]
    predictions_filtered.index = predictions_filtered.reset_index().index

    # Get list with count of matching subsequent windows
    sub_windows = (predictions_filtered != predictions_filtered.shift()).cumsum()
    # Count the number of consecutive windows with the same label
    counted_windows = predictions_filtered.groupby(sub_windows).transform('size')

    # Get indices of single windows
    test = np.where([counted_windows <= filter_length])[1]

    # Iterate through single prediction windows
    for index in test:
        # If there is a previous row
        if index > 0:
            # Replace predicted activity by previous prediction
            predictions_filtered.at[index] = predictions_filtered.at[index - 1]
        else:
            # Replace predicted activity by subsequent prediction
            predictions_filtered.at[index] = predictions_filtered.at[index + 1]

    return predictions_filtered.to_numpy()


def plot_figure(df, title_string):
    # Plot IMU data and heart rate
    fig = plt.figure()

    # Define y-label order by plotting dummy data
    cycle = plt.rcParams['axes.prop_cycle'].by_key()['color']
    axes = plt.plot([df.at[0, 'Time'], df.at[1, 'Time'], df.at[2, 'Time'], df.at[3, 'Time'],
                     df.at[4, 'Time']], ['lying', 'sit', 'stand', 'walk', 'stairs'])
    # Remove dummy data
    [u.remove() for u in axes]

    # Plot predictions
    plt.plot(df['Time'], df['activity_prediction'], color=cycle[0], label="Raw Predictions")
    plt.plot(df['Time'], df['filtered_prediction'], color=cycle[1], label="Filtered Predictions")

    # Add axes labels and title
    plt.xlabel('Time')
    plt.ylabel('Predictions')
    plt.title(title_string)
    plt.legend()

    # Increase plot to full screen (exit by pressing Q)
    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()

    # Remove top and right axes and show plot
    sns.despine()
    plt.show()

    return fig


def get_sensor_set(sensors):
    # Initialize value for sensor check {'wrist_l', 'wrist_r', 'ankle_l', 'ankle_r', 'chest'}
    sensor_num = 0
    # Check what sensors are available
    if 'wrist_l' in sensors:
        sensor_num += 10000
    if 'wrist_r' in sensors:
        sensor_num += 1000
    if 'ankle_l' in sensors:
        sensor_num += 100
    if 'ankle_r' in sensors:
        sensor_num += 10
    if 'chest' in sensors:
        sensor_num += 1

    # Check for valid sensor combinations
    # TODO: More possible combinations that could be handled differently
    # wrists    (11000)
    if sensor_num == 11000:
        return 'wrists'
    # ankles      (110)
    elif sensor_num == 110:
        return 'ankles'
    # all       (11111)
    elif sensor_num == 11111:
        return 'all'
    # no_chest  (11110)
    elif sensor_num == 11110:
        return 'no_chest'
    # left      (10100)
    elif sensor_num == 10100:
        return 'left'
    # right      (1010)
    elif sensor_num == 1010:
        return 'right'
    elif sensor_num == 11100 or sensor_num == 11010:
        print("One missing ankle sensor. Computing output only based on wrists.")
        return 'wrists'
    elif sensor_num == 10110 or sensor_num == 1110:
        print("One missing wrist sensor. Computing output only based on ankles.")
        return 'ankles'
    else:
        return 'invalid'


def predict_activity(
        merged_data: pd.DataFrame,
        out_filename: str,
        sensors
):
    # Check if recording contains valid sensor set
    sensor_set = get_sensor_set(sensors)

    # If there is no valid sensor set
    if (sensor_set == 'invalid'):
        return pd.DataFrame()
    else:
        param_sensors = sensor_set

    #param_sensors = 'no_chest'
    param_output_location = None
    param_affected = False
    param_standardization = True
    param_append = False

    # Get activity predictions
    activ_predict = main(out_filename, merged_data, param_sensors, param_output_location,
                                     affected=param_affected,
                                     no_inperson_standardization=param_standardization, append=param_append)

    return activ_predict
