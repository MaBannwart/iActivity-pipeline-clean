from math import floor
import pandas as pd
import numpy as np
from agcounts.extract import get_counts
from datetime import datetime
import utils.constants as constants
import utils.functions as utils
import os


class HL7Data:
    def __init__(self, PatID, FallID, Date):
        self.PatID = PatID
        self.FallID = FallID
        self.Time = Date
        self.Data = None
        self.AllSensors = ['wrist_r', 'wrist_l', 'ankle_r', 'ankle_l', 'chest']

    def get_hl7append(self, index, shift):
        append = F"OBX|{1 + shift * 7}|NM|{self.Data[index][0]}_Total||{self.Data[index][1]}||||||F|\n"

        for hour in range(1, 7):
            if hour <= self.Data[1][1] + 1:
                append += F"OBX|{hour + 1 + shift * 7}|NM|{self.Data[index][0]}_Hour{hour}||{self.Data[index][hour + 1]}||||||F|\n"
            else:
                append += F"OBX|{hour + 1 + shift * 7}|NM|{self.Data[index][0]}_Hour{hour}||||||F|\n"

        return append

    def get_hl7default(self, pos, shift):
        return F"OBX|{1 + shift * 7}|NM|{pos}_Total||||||||F|\n" + \
            F"OBX|{2 + shift * 7}|NM|{pos}_Hour1||||||||F|\n" + \
            F"OBX|{3 + shift * 7}|NM|{pos}_Hour2||||||||F|\n" + \
            F"OBX|{4 + shift * 7}|NM|{pos}_Hour3||||||||F|\n" + \
            F"OBX|{5 + shift * 7}|NM|{pos}_Hour4||||||||F|\n" + \
            F"OBX|{6 + shift * 7}|NM|{pos}_Hour5||||||||F|\n" + \
            F"OBX|{7 + shift * 7}|NM|{pos}_Hour6||||||||F|\n"


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

    # Define file name
    #directory = constants.HOME + "output/" + patient_details.pid + "/iactivity/" + patient_details.date_stamp

    #if not os.path.isdir(directory):
    #    os.makedirs(directory)

    #filename = directory + "/" + patient_details.pid + '_counts_meta.csv'

    data = get_append_data(counts, positions, epoch, patient_details)
    #file = open(filename, 'w', newline='')
    #writer = csv.writer(file)
    #writer.writerows(data)
    #file.close()

    # Average counts per minute instead of seconds
    #counts_resampled = counts.groupby(np.arange(len(counts.index)) // 60).mean()

    #filename = directory + "/" + patient_details.pid + '_counts.csv'
    #counts_resampled.to_csv(filename, mode='w', index=False)

    return data, counts


def csv_to_hl7(hl7data, patient_details):
    print('Currently assembling HL7')
    current_date = datetime.now()
    current_date = current_date.strftime('%Y%m%d%h')

    base = F"MSH|^~\&|GaitUp|ALL|KIS|ALL|{hl7data.Time}||ORU^R01|888|P|2.2\n" + \
           F"PID||{hl7data.PatID}|||||||\n" + \
           F"PV1|||||||||||||||||||{hl7data.FallID}\n" + \
           F"OBR|1|GaitUp||ActivityMonitoring|||{hl7data.Time}||||||||||||||||||F|\n"

    first_column = [row[0] for row in hl7data.Data]
    for i in range(len(hl7data.AllSensors)):
        pos = hl7data.AllSensors[i]
        if pos in first_column:
            index = first_column.index(pos)
            base = base + hl7data.get_hl7append(index, i)
        else:
            base = base + hl7data.get_hl7default(pos, i)

    directory = constants.HOME + "output/" + patient_details.pid + "/iactivity/" + patient_details.date_stamp

    if not os.path.isdir(directory):
        os.makedirs(directory)

    filename = directory + "/" + hl7data.PatID + '_hl7.hl7'
    hl7_file = open(filename, "w+")
    hl7_file.write(base)
    hl7_file.close()

    filename = constants.OUTPUT_FOLDER_HL7 + "/" + hl7data.PatID + '_hl7.hl7'
    hl7_file = open(filename, "w+")
    hl7_file.write(base)
    hl7_file.close()


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
    # Maybe later in Details
    #pid, fid, date_stamp = utils.get_details(filename)
    #patient_details = utils.PatientDetails(pid, fid, date_stamp)
    hl7data = HL7Data(PatID=patient_details.pid, FallID=patient_details.fid, Date=patient_details.date_stamp)

    counts = raw_to_counts(data, sensors, freq, epoch)
    hl7data.Data, counts = counts_to_csv(counts, sensors, patient_details, epoch)
    #csv_to_hl7(hl7data, patient_details)
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