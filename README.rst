iActivity Processing Pipeline
===========

.. image:: ./logo.png
    :alt: Gaitalytics Logo
    :align: center
    :width: 200px

This Python project provides the code for processing clinical axivity (AX6) sensor data in .cwa format.
Prior to utilizing this codebase, sensor data has to be present in the correct folder structure and named
according to a given template.

This repository is an extension from a previous processing pipeline based on the XSens Dots movement sensors.
There is an ongoing addition of algorithms for calculating sensor-based outcomes.


Functionalities
---------------

Input
^^^^^
CWA or WAV files (can also be individually zipped to safe storage space) from AX6 sensors worn on the wrists or ankles.
  
The filename of the raw data files has to fit the following structure:
  
"F" + FID + _ + measurement_start_date + _ + "Set" + set_number + _ + sensor_location + _ + sensor_id + _ + session_id + ".cwa"
  
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| variable           | Description                                                                                                                                                             |
+====================+=========================================================================================================================================================================+
| FID                | clinical patient fall number                                                                                                                                            |
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| measure_start_date | The date of the first timestamp in the raw data in the format YYYYMMDD                                                                                                  |
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| set_number         | Set number given from the AX6 inventory file (MS Teams: Collaborative Projects > iActivity channel > Docs running process > Sensors_Materials)                          |
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| sensor_location    | One of 4 sensor location abbreviations: WR, WL, AR, AL (wrist right, wrist left, ankle right, ankle left)                                                               |
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| sensor_id          | The unique sensor serial number printed onto the sensors by the manufacturer                                                                                            |
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| session_id         | Ten digit number starting at 0000000000 counting the sessions that have been recorded. Increases everytime raw data is transfered via the automatic data transfer tool. |
+--------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
.. note::
    Filenames with the same < "F" + FID + _ measure_start_date > string are grouped and their data is merged together.


Outcomes
^^^^^^^^^^^^^^^
Currently the following outcomes are available

+------------------+-----------------------------+------------------+
| Outcome          | Description                 | Link             |
+==================+=============================+==================+
| Wear time        | van Hees et al. 2011 [1]    | `calc_wtv`_      |
+------------------+-----------------------------+------------------+
| Activity Count   | Neishabouri et al. 2022 [2] | `act_counts`_    |
+------------------+-----------------------------+------------------+
| Gait/No-gait     | Pohl et al. 2022 [3]        | `gait_posture`_. |
+------------------+-----------------------------+------------------+
| Activity/Posture | Pohl et al. 2022 [3]        | `gait_posture`_. |
+------------------+-----------------------------+------------------+
| Arm Symmetry     | From counts                 |                  |
+------------------+-----------------------------+------------------+
| Activity Levels  | From counts                 |                  |
+------------------+-----------------------------+------------------+
| Step counts      | From dominant wrist counts  | `step_count`_.   |
+------------------+-----------------------------+------------------+

.. _calc_wtv: https://github.com/digitalinteraction/openmovement-python/blob/master/src/openmovement/process/calc_wtv.py
.. _act_counts: https://github.com/actigraph/agcounts
.. _gait_posture: https://github.com/StimuLOOP/activity-detection
.. _step_count: https://github.com/OxWearables/stepcount
  

References
""""""""""

[1] van Hees et al. 2011. Estimation of daily energy expenditure in pregnant and non-pregnant women using a wrist-worn tri-axial accelerometer. PloS one, 6(7), e22922.
  
[2] Neishabouri et al. 2022. Quantification of acceleration as activity counts in ActiGraph wearable. Sci Rep., 12(1), 11958.
  
[3] Pohl et al. 2022. Accuracy of gait and posture classification using movement sensors in individuals with mobility impairment after stroke. Front Physiol., 26(13), 933987.


Quickstart
----------

Installation
^^^^^^^^^^^^

In a command shell or terminal:

Move to the parent folder of the project
- cd parentProjectFolder 

Clone the repository
- git clone https://github.com/MaBannwart/iActivity-pipeline-clean.git

Enter into the project folder
- cd your-project

Install uv package and project manager
- pip install uv 

Automatically creat the virtual environment, install dependencies and python version
- uv sync


Run Pipeline
^^^^^^^^^^^^^

Copy or move raw data files (.cwa, .wav, .zip) to the "../data/Input" folder

Rename the files according to the following schema: 
FID_Date_Set_Location_SensorID_SessionID (e.g. F1234567_20260310_Set1_WL_6028005_0000000001.zip)

In a terminal:
- uv run main.py


Outcomes
^^^^^^^^

Find calculated outcomes as .csv file in the OUTPUT folder
