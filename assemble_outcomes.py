import pandas as pd

def assemble_data(fn_database, merged_data, wear_time, counts, gait_predictions, activity_predictions, durations_resampled, activity_levels, step_count):
    # Assemble outcomes for database
    print("Assembling outcomes for database")
    df_out = pd.DataFrame()
    if gait_predictions is not None and 'Time' in gait_predictions:
        df_out['Timestamp'] = gait_predictions['Time']
    elif activity_predictions is not None and 'Time' in activity_predictions:
        df_out['Timestamp'] = activity_predictions['Time']
    else:
        # Get timestamps without predictions
        # num_windows = len(merged_data.index) // 128
        # data_length = num_windows * 128
        df_out.insert(0, 'Time', merged_data['Timestamps'])
        # df_out.insert(1, 'Temperature_AR', merged_data['ankle_r__temp'])
        # df_out.insert(2, 'Temperature_AL', merged_data['ankle_l__temp'])
        # df_out.insert(3, 'Temperature_WR', merged_data['wrist_r__temp'])
        # df_out.insert(4, 'Temperature_WL', merged_data['wrist_l__temp'])
        # df_out.insert(5, 'Light_AR', merged_data['ankle_r__light'])
        # df_out.insert(6, 'Light_AL', merged_data['ankle_l__light'])
        # df_out.insert(7, 'Light_WR', merged_data['wrist_r__light'])
        # df_out.insert(8, 'Light_WL', merged_data['wrist_l__light'])
        df_out.set_index('Time', inplace=True)
        df_out = df_out.resample('1min').mean()  # .apply(lambda x: mode(x))
        # df_resampled.reset_index(level=0, inplace=True)
        df_out.index.name = 'Timestamp'
        df_out.reset_index(inplace=True)



    if counts is not None and 'wrist_r__AC' in counts.columns:
        df_out['AC_wrist_r'] = counts['wrist_r__AC']
    else:
        df_out['AC_wrist_r'] = float("NaN")

    if counts is not None and 'wrist_l__AC' in counts.columns:
        df_out['AC_wrist_l'] = counts['wrist_l__AC']
    else:
        df_out['AC_wrist_l'] = float("NaN")

    if counts is not None and 'ankle_r__AC' in counts.columns:
        df_out['AC_ankle_r'] = counts['ankle_r__AC']
    else:
        df_out['AC_ankle_r'] = float("NaN")

    if counts is not None and 'ankle_l__AC' in counts.columns:
        df_out['AC_ankle_l'] = counts['ankle_l__AC']
    else:
        df_out['AC_ankle_l'] = float("NaN")


    # Old outcomes
    # if df_out['AC_wrist_r'].isna().all():
    #     df_out['act_total_wrist_r'] = float("NaN")
    # else:
    #     df_out['act_total_wrist_r'] = df_out['AC_wrist_r'] > 2
    # if df_out['AC_wrist_l'].isna().all():
    #     df_out['act_total_wrist_l'] = float("NaN")
    # else:
    #     df_out['act_total_wrist_l'] = df_out['AC_wrist_l'] > 2
    #
    # if df_out['act_total_wrist_r'].isna().all() and df_out['act_total_wrist_l'].isna().all():
    #     df_out['act_unilateral_wrist_r'] = float("NaN")
    #     df_out['act_unilateral_wrist_l'] = float("NaN")
    #     df_out['act_bilateral'] = float("NaN")
    # else:
    #     df_out['act_unilateral_wrist_r'] = np.logical_and(df_out['act_total_wrist_r'] > 0,
    #                                                         df_out['act_total_wrist_l'] < 1)
    #     df_out['act_unilateral_wrist_l'] = np.logical_and(df_out['act_total_wrist_r'] < 1,
    #                                                         df_out['act_total_wrist_l'] > 0)
    #     df_out['act_bilateral'] = np.logical_and(df_out['act_total_wrist_r'] > 0, df_out['act_total_wrist_l'] > 0)



    # New outcomes
    if durations_resampled is not None and 'act_total_wrist_r' in durations_resampled.columns:
       df_out['act_total_wrist_r'] = durations_resampled['act_total_wrist_r']
    else:
       df_out['act_total_wrist_r'] = float("NaN")

    if durations_resampled is not None and 'act_total_wrist_l' in durations_resampled.columns:
       df_out['act_total_wrist_l'] = durations_resampled['act_total_wrist_l']
    else:
       df_out['act_total_wrist_l'] = float("NaN")


    if durations_resampled is not None and 'act_unilateral_wrist_r' in durations_resampled.columns:
       df_out['act_unilateral_wrist_r'] = durations_resampled['act_unilateral_wrist_r']
    else:
       df_out['act_unilateral_wrist_r'] = float("NaN")

    if durations_resampled is not None and 'act_unilateral_wrist_l' in durations_resampled.columns:
       df_out['act_unilateral_wrist_l'] = durations_resampled['act_unilateral_wrist_l']
    else:
       df_out['act_unilateral_wrist_l'] = float("NaN")


    if durations_resampled is not None and 'act_bilateral' in durations_resampled.columns:
       df_out['act_bilateral'] = durations_resampled['act_bilateral']
    else:
       df_out['act_bilateral'] = float("NaN")


    if activity_levels is not None and 'Sedentary' in activity_levels.columns:
       df_out['Sedentary'] = activity_levels['Sedentary']
    else:
       df_out['Sedentary'] = float("NaN")

    if activity_levels is not None and 'Low' in activity_levels.columns:
       df_out['Low'] = activity_levels['Low']
    else:
       df_out['Low'] = float("NaN")

    if activity_levels is not None and 'Moderate' in activity_levels.columns:
       df_out['Moderate'] = activity_levels['Moderate']
    else:
       df_out['Moderate'] = float("NaN")

    if activity_levels is not None and 'Vigorous' in activity_levels.columns:
       df_out['Vigorous'] = activity_levels['Vigorous']
    else:
       df_out['Vigorous'] = float("NaN")

    # Add a column with the maximum activity level per minute
    df_out['activity_level'] = df_out[['Sedentary', 'Low', 'Moderate', 'Vigorous']].idxmax(axis=1)


    if step_count is not None and 'Steps' in step_count.columns:
         df_out['Steps'] = step_count['Steps']
    else:
        df_out['Steps'] = float("NaN")

    # Gait detection based on step
    df_out.dropna(inplace=True)
    df_out['gait_nogait_new'] = df_out['Steps'].apply(lambda x: 'gait' if x > 0 else 'no-gait')



    if gait_predictions is not None and 'filtered_prediction' in gait_predictions:
        df_out['gait_nogait'] = gait_predictions['filtered_prediction']
    else:
        df_out['gait_nogait'] = float("NaN")

    if activity_predictions is not None and 'filtered_prediction' in activity_predictions:
        df_out['gait_posture'] = activity_predictions['filtered_prediction']
    else:
        df_out['gait_posture'] = float("NaN")



    df_out['HR'] = float("NaN")



    if wear_time is not None:
        df_out = df_out.merge(wear_time, how='inner', on='Timestamp')
    else:
        df_out['WT_wrist_r'] = float("NaN")
        df_out['WT_wrist_l'] = float("NaN")
        df_out['WT_ankle_r'] = float("NaN")
        df_out['WT_ankle_l'] = float("NaN")

    df_out.replace({False: 0, True: 1}, inplace=True)
    # df_out.astype(float)
    df_out.to_csv(fn_database, index=False)

    return df_out