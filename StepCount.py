# ------------------------------------------------------------------------------------------------------------
# Code adapted from https://github.com/OxWearables/stepcount/tree/main
# ------------------------------------------------------------------------------------------------------------

import pathlib
import time
import numpy as np
import pandas as pd
import joblib
import actipy
import utils.constants as constants
from experimental.resample import resample_fixed


def get_step_count(merged_data, filepath, dominant_wrist):
    """Calculate the step count per minute.

    Parameters
    ----------
    filepath (str):
        The path to the raw file corresponding to the dominant wrist.

    Returns
    -------
    minutely :
        The number of steps per minute.
    """

    def _is_enough(x, min_wear=None, dt=None):
        if min_wear is None:
            return True  # no minimum wear time, then default to True
        if dt is None:
            dt = infer_freq(x.index).total_seconds()    #get sampling frequency (timedelta)
        return x.notna().sum() * dt / 60 > min_wear

    def _sum(x, min_wear=None, dt=None):
        if x.isna().all():  # have to explicitly check this because pandas' .sum() returns 0 if all-NaN
            return np.nan
        if not _is_enough(x, min_wear, dt):
            return np.nan
        return x.sum()

    # TODO: Make robust against differently configured IMU sampling frequency
    freq = constants.FREQ_IMU

    stepInput_data = merged_data[['Timestamps', dominant_wrist + '__acc_x', dominant_wrist + '__acc_y', dominant_wrist + '__acc_z']].to_numpy(copy=True)
    # Convert to numpy datetime64 (ns precision)
    stepInput_data[:, 0] = stepInput_data[:, 0].astype('datetime64[ns]')
    # Resample data to 30 Hz
    stepInput_data = resample_fixed(stepInput_data, use_time=True, in_frequency=50, out_frequency=30, lp_filter=True, interpolation_mode='linear')
    # Convert back to dataframe with column names

    stepInput_data = pd.DataFrame(stepInput_data, columns=['time', 'x', 'y', 'z'])
    stepInput_data['time'] = pd.to_datetime(stepInput_data['time'])
    stepInput_data.set_index('time', inplace=True)

    # Load file
    #processed_data, _ = read(
    #    filepath,
    #    usecols='time,x,y,z',
    #    resample_hz=30,
    #    sample_rate=freq,
    #    verbose=False
    #)

    # Debug code
    #stepInput_data.to_csv('C:/Users/bannw/Downloads/stepInput_data.csv', index=True)
    #processed_data.to_csv('C:/Users/bannw/Downloads/read_data.csv', index=True)

    # Define the path to the model file
    model_path = pathlib.Path(__file__).parent / "models/steps/ssl-20230208.joblib.lzma"

    # Load the model directly
    print("Loading model...")
    model = joblib.load(model_path)

    # TODO: Do not hardcode parameters in different locations
    # Set up model attributes
    model.sample_rate = 30
    model.window_len = int(np.ceil(30 * model.window_sec))
    model.wd.sample_rate = 30
    model.wd.device = 'cpu'

    Y, _, _ = model.predict_from_frame(stepInput_data)
    #Y2, _, _ = model.predict_from_frame(processed_data)

    minutely_steps = Y.resample('T').agg(_sum).rename('Steps')
    minutely_steps = minutely_steps.round().astype(pd.Int64Dtype())

    # Save minutely data
    minutely = pd.concat([
        minutely_steps
    ], axis=1)
    minutely.reset_index(inplace=True)

    # Debug code
    #minutely.to_csv('C:/Users/bannw/Downloads/step_data_1.csv', index=False)

    return minutely


def read(
        filepath: str,
        usecols: str = 'time,x,y,z',
        resample_hz: str = 'uniform',
        sample_rate: float = None,
        verbose: bool = True
):
    """
    Read and preprocess activity data from a file.

    This function reads activity data from various file formats, processes it using the `actipy` library,
    and returns the processed data along with metadata information.

    Parameters:
    - filepath (str): The path to the file containing activity data.
    - usecols (str, optional): A comma-separated string of column names to use when reading CSV files.
      Default is 'time,x,y,z'.
    - resample_hz (str, optional): The resampling frequency for the data. If 'uniform', it will use `sample_rate`
      and resample to ensure it is evenly spaced. Default is 'uniform'.
    - sample_rate (float, optional): The sample rate of the data. If None, it will be inferred. Default is None.
    - verbose (bool, optional): If True, enables verbose output during processing. Default is True.

    Returns:
    - tuple: A tuple containing:
        - data (pd.DataFrame): The processed activity data.
        - info (dict): A dictionary containing metadata information about the data.

    Raises:
    - ValueError: If the file format is unknown or unsupported.

    Example:
        data, info = read('activity_data.csv')
    """

    p = pathlib.Path(filepath)
    fsize = round(p.stat().st_size / (1024 * 1024), 1)
    ftype = p.suffix.lower()
    if ftype in (".gz", ".xz", ".lzma", ".bz2", ".zip"):  # if file is compressed, check the next extension
        ftype = pathlib.Path(p.stem).suffix.lower()

    if ftype in (".csv", ".pkl"):

        if ftype == ".csv":
            tcol, xcol, ycol, zcol = usecols.split(',')
            data = pd.read_csv(
                filepath,
                usecols=[tcol, xcol, ycol, zcol],
                parse_dates=[tcol],
                index_col=tcol,
                dtype={xcol: 'f4', ycol: 'f4', zcol: 'f4'},
            )
            # rename to standard names
            data = data.rename(columns={xcol: 'x', ycol: 'y', zcol: 'z'})
            data.index.name = 'time'

        elif ftype == ".pkl":
            data = pd.read_pickle(filepath)

        else:
            raise ValueError(f"Unknown file format: {ftype}")

        if sample_rate in (None, False):
            freq = infer_freq(data.index)
            sample_rate = int(np.round(pd.Timedelta('1s') / freq))

        # Quick fix: Drop duplicate indices. TODO: Maybe should be handled by actipy.
        data = data[~data.index.duplicated(keep='first')]

        data, info = actipy.process(
            data, sample_rate,
            lowpass_hz=None,
            calibrate_gravity=True,
            detect_nonwear=True,
            resample_hz=resample_hz,
            verbose=verbose,
        )

        info.update({
            "Filename": filepath,
            "Device": ftype,
            "Filesize(MB)": fsize,
            "SampleRate": sample_rate,
            "StartTime": data.index[0].strftime('%Y-%m-%d %H:%M:%S'),
            "EndTime": data.index[-1].strftime('%Y-%m-%d %H:%M:%S')
        })

    elif ftype in (".cwa", ".gt3x", ".bin"):

        data, info = actipy.read_device(
            filepath,
            lowpass_hz=None,
            calibrate_gravity=True,
            detect_nonwear=True,
            resample_hz=resample_hz,
            verbose=verbose,
        )

    else:
        raise ValueError(f"Unknown file format: {ftype}")

    if 'ResampleRate' not in info:
        info['ResampleRate'] = info['SampleRate']

    return data, info


def infer_freq(t):
    """ Like pd.infer_freq but more forgiving """
    tdiff = t.to_series().diff()    #get time stamp differences
    q1, q3 = tdiff.quantile([0.25, 0.75])   #get first and third quartiles
    tdiff = tdiff[(q1 <= tdiff) & (tdiff <= q3)]    #remove values outside of the first and third quartiles range
    freq = tdiff.mean() #calculate sampling frequency as mean of the remaining time stamp differences
    freq = pd.Timedelta(freq)   #convert datetime to timedelta
    return freq