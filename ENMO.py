import pandas as pd
import numpy as np
import utils.constants as constants


def raw_to_ENMO(data, position, freq):
    """
    Calculate ENMO for a specific sensor position.

    Parameters
    ----------
    data : pd.DataFrame
        DataFrame containing the raw accelerometer data.
    position : str
        The sensor position (e.g., 'wrist_l', 'wrist_r') for which to calculate ENMO.
    freq : int
        Sampling frequency of the data (Hz).

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the ENMO values resampled to the specified epoch length.
    """

    # Fixed 5-second epoch length
    epoch_seconds = 5

    # Select the accelerometer columns for the specified position
    raw = data[[position + "__acc_x", position + "__acc_y", position + "__acc_z"]]
    raw = np.array(raw)

    # Calculate Vector Magnitude (VM)
    vm = np.sqrt(np.sum(raw ** 2, axis=1))

    # Calculate ENMO (Tsanas, 2022)
    enmo = (vm - 1.0) * 1000.0
    enmo[enmo < 0] = 0

    # Calculate the number of samples per epoch
    samples_per_epoch = freq * epoch_seconds

    # Reshape the data into epochs and calculate the mean ENMO per epoch
    n_epochs = len(enmo) // samples_per_epoch
    reshaped_enmo = enmo[:n_epochs * samples_per_epoch].reshape((n_epochs, samples_per_epoch))
    enmo_resampled = np.mean(reshaped_enmo, axis=1)

    # Create a DataFrame with the averaged ENMO values
    enmo_resampled_df = pd.DataFrame(enmo_resampled, columns=["ENMO"])

    return enmo_resampled_df


def ENMO_to_levels(enmo):
    """
    Calculate the time (in sec) spent in each activity level (Sedentary, Low, Moderate, Vigorous) per minute.
    The thresholds were derived from "Comparison of diferent software for processing physical activity measurements with accelerometry", Verhoog et al. (2023)

    Parameters
    ----------
    enmo : list or DataFrame
        The ENMO data

    Returns
    -------
    activity_levels : DataFrame
        A DataFrame with activity levels resampled to 1-minute intervals.
    """

    # Initialize DataFrame for storing the activity level counts
    actdummy = pd.DataFrame(enmo, columns=["ENMO"])

    # Define thresholds for activity levels (in mg)
    sedentary_threshold = 48
    low_threshold = 154
    moderate_threshold = 389

    # Initialize columns for each activity level
    actdummy["Sedentary"] = 0
    actdummy["Low"] = 0
    actdummy["Moderate"] = 0
    actdummy["Vigorous"] = 0

    # Classify ENMO values into activity levels
    actdummy.loc[actdummy["ENMO"] < sedentary_threshold, "Sedentary"] = 5
    actdummy.loc[(actdummy["ENMO"] >= sedentary_threshold) & (actdummy["ENMO"] < low_threshold), "Low"] = 5
    actdummy.loc[(actdummy["ENMO"] >= low_threshold) & (actdummy["ENMO"] < moderate_threshold), "Moderate"] = 5
    actdummy.loc[actdummy["ENMO"] >= moderate_threshold, "Vigorous"] = 5

    # Resample the data to 1-minute intervals by summing the classified seconds to get the seconds spent per activity level per minute
    activity_level = actdummy.groupby(np.arange(len(actdummy.index)) // 12).sum()

    return activity_level


def get_activity_levels(
        data: pd.DataFrame,
        position: str
):
    freq = constants.FREQ_IMU

    enmo = raw_to_ENMO(data, position, freq)
    activity_level = ENMO_to_levels(enmo)

    return activity_level