from math import floor
import pandas as pd
import numpy as np
from agcounts.extract import get_counts
from datetime import datetime
import utils.constants as constants
import utils.functions as utils


def raw_to_counts(data, positions, freq, epoch):
    countspos = []
    for pos in positions:
        print(f"Currently working on Position {pos}")
        raw = data[[pos + "__acc_x", pos + "__acc_y", pos + "__acc_z"]]
        raw = np.array(raw)
        counts = get_counts(raw, freq=freq, epoch=epoch, fast=True, use_mne=False)
        countspos.append(counts)
    return countspos


def get_append_data(counts, positions, epoch, patient_details):
    IterationLength = 3600 / epoch
    Iterations = floor(len(counts[positions[0] + "__AC"]) / IterationLength)
    '''data = [['Epoch: ', epoch], ['Iterations: ', Iterations],
            ['Sensor', 'Total', 'Hour 1', 'Hour 2', 'Hour 3', 'Hour 4', 'Hour 5', 'Hour 6']]'''
    data = [['Epoch', 'Iterations', 'Start Time'], [epoch, Iterations, patient_details.date_stamp],
            ['Sensor', 'Total', 'Hour 1', 'Hour 2', 'Hour 3', 'Hour 4', 'Hour 5', 'Hour 6']]

    for pos in positions:
        posdata = [pos, counts[pos + "__AC"].mean()]

        for i in range(Iterations):
            posdata.append(counts[pos + "__AC"][round(i * IterationLength):round((i + 1) * IterationLength)].mean())

        posdata.append(counts[pos + "__AC"][round(Iterations * IterationLength):].mean())

        data.append(posdata)

    return data


def counts_to_csv(countspos, positions, patient_details, epoch):
    print(f"Currently assembling the csv")

    counts = pd.DataFrame()
    summarycounts = pd.DataFrame()
    uexcounter = 0
    lexcounter = 0
    for posindex in range(len(positions)):
        pos = positions[posindex]
        countsdummy = pd.DataFrame(countspos[posindex], columns=[pos + "__X", pos + "__Y", pos + "__Z"])
        countsdummy[pos + "__AC"] = (countsdummy[pos + "__X"] ** 2
                                     + countsdummy[pos + "__Y"] ** 2
                                     + countsdummy[pos + "__Z"] ** 2) ** 0.5

        if 'wrist' in pos:
            uexcounter += 1
            if uexcounter == 1:
                summarycounts['upperex'] = countsdummy[pos + "__AC"]
            else:
                summarycounts['upperex'] = (summarycounts['upperex'] + countsdummy[pos + "__AC"]) / uexcounter

        if 'ankle' in pos:
            lexcounter += 1
            if lexcounter == 1:
                summarycounts['lowerex'] = countsdummy[pos + "__AC"]
            else:
                summarycounts['lowerex'] = (summarycounts['lowerex'] + countsdummy[pos + "__AC"]) / lexcounter
        counts = pd.concat([counts, countsdummy], axis=1)
    counts = pd.concat([counts, summarycounts], axis=1)

    data = get_append_data(counts, positions, epoch, patient_details)

    return data, counts


def plot_counts(counts_csv, axes=None):
    pass


def get_activity_counts(
        data: pd.DataFrame,
        sensors: list[str],
        patient_details: utils.PatientDetails
):
    """

    Parameters
    ----------


    Returns
    -------
    """
    freq = constants.FREQ_IMU
    epoch = constants.EPOCH_LENGTH

    counts = raw_to_counts(data, sensors, freq, epoch)
    data, counts = counts_to_csv(counts, sensors, patient_details, epoch)
    return counts, patient_details


def get_activity_durations(counts):
    """Calculate arm use durations (total, unilateral and bilateral).

    Parameters
    ----------
    counts:
        Dataframe containing activity counts for each position

    Returns
    -------
    durations :
        Dataframe containing the arm use durations
    """

    durations = pd.DataFrame()

    if counts['wrist_r__AC'].isna().all():
        durations['act_total_wrist_r'] = float("NaN")
    else:
        # A second is considered active when AC > 2
        durations['act_total_wrist_r'] = counts['wrist_r__AC'] > 2

    if counts['wrist_l__AC'].isna().all():
        durations['act_total_wrist_l'] = float("NaN")
    else:
        durations['act_total_wrist_l'] = counts['wrist_l__AC'] > 2

    if durations['act_total_wrist_r'].isna().all() and durations['act_total_wrist_l'].isna().all():
        durations['act_unilateral_wrist_r'] = float("NaN")
        durations['act_unilateral_wrist_l'] = float("NaN")
        durations['act_bilateral'] = float("NaN")
    else:
        # Unilateral activity when only one wrist is active
        durations['act_unilateral_wrist_r'] = np.logical_and(durations['act_total_wrist_r'] > 0,
                                                             durations['act_total_wrist_l'] < 1)
        durations['act_unilateral_wrist_l'] = np.logical_and(durations['act_total_wrist_r'] < 1,
                                                             durations['act_total_wrist_l'] > 0)
        # Bilateral activity when both wrists are active
        durations['act_bilateral'] = np.logical_and(durations['act_total_wrist_r'] > 0,
                                                    durations['act_total_wrist_l'] > 0)

    return durations


def get_dominant_wrist(counts):
    """Determine the dominant wrist.

    Parameters
    ----------
    counts:
        Dataframe containing activity counts for each position

    Returns
    -------
    dominant_wrist :
        The dominant wrist
    """

    wrist_positions = ['wrist_l', 'wrist_r']
    total_counts = {}

    # Calculate the total AC for both wrists
    for pos in wrist_positions:
        if (pos + "__AC") in counts:
            total_counts[pos] = counts[pos + "__AC"].sum()
        else:
            print(f"Warning: No activity counts column found for {pos}")

    # Identify the dominant wrist
    dominant_wrist = max(total_counts, key=total_counts.get)

    if dominant_wrist == "wrist_l":
        print(f"The dominant wrist is the left one.")
    else:
        print(f"The dominant wrist is the right one.")

    return dominant_wrist