import pandas as pd
import numpy as np

def safe_assign(target_df, source_df, column_mapping):
    """
    Safely maps columns from a source DataFrame to a target DataFrame.
    If the source or column is missing, assigns NaN.
    
    Parameters
    ----------
    target_df : pd.DataFrame
    source_df : pd.DataFrame | None
    column_mapping : dict
        {target_column: source_column}
    """
    
    for target_col, source_col in column_mapping.items():
        if source_df is None or source_col not in source_df.columns:
            target_df[target_col] = np.nan
            continue
            
        series = source_df[source_col]
                           
        # Align by index if possible
        if len(series) == len(target_df):
            target_df[target_col] = series.values
        else:
            target_df[target_col] = series.reindex(target_df.index).values


def build_timestamp_df(merged_data, gait_predictions, activity_predictions):
    """Determine timestamp source and construct base dataframe."""

    if gait_predictions is not None and "Time" in gait_predictions:
        return pd.DataFrame({"Timestamp": gait_predictions["Time"]})

    if activity_predictions is not None and "Time" in activity_predictions:
        return pd.DataFrame({"Timestamp": activity_predictions["Time"]})

    # fallback: derive timestamps from raw data
    df = pd.DataFrame({"Time": merged_data["Timestamps"]})
    df.set_index("Time", inplace=True)

    df = df.resample("1min").mean()
    df.index.name = "Timestamp"

    return df.reset_index()  
            

def assemble_data(outcome_path, merged_data, wear_time, counts, gait_predictions, 
                  activity_predictions, durations_min, activity_levels, step_count):
    """Assembles all calculated outcomes into a single unified dataframe."""

    df_out = build_timestamp_df(merged_data, gait_predictions, activity_predictions)

    # -------------------------------------------------
    # Counts
    # -------------------------------------------------

    safe_assign(
        df_out,
        counts,
        {
            "AC_wrist_r": "wrist_r__AC",
            "AC_wrist_l": "wrist_l__AC",
            "AC_ankle_r": "ankle_r__AC",
            "AC_ankle_l": "ankle_l__AC",
        },
    )

# -------------------------------------------------
    # Activity durations
    # -------------------------------------------------

    safe_assign(
        df_out,
        durations_min,
        {
            "act_total_wrist_r": "act_total_wrist_r",
            "act_total_wrist_l": "act_total_wrist_l",
            "act_unilateral_wrist_r": "act_unilateral_wrist_r",
            "act_unilateral_wrist_l": "act_unilateral_wrist_l",
            "act_bilateral": "act_bilateral",
        },
    )

    # -------------------------------------------------
    # Activity levels
    # -------------------------------------------------

    safe_assign(
        df_out,
        activity_levels,
        {
            "Sedentary": "Sedentary",
            "Low": "Low",
            "Moderate": "Moderate",
            "Vigorous": "Vigorous",
        },
    )

    df_out["activity_level"] = (
        df_out[["Sedentary", "Low", "Moderate", "Vigorous"]]
        .idxmax(axis=1)
        .where(~df_out[["Sedentary", "Low", "Moderate", "Vigorous"]].isna().all(axis=1))
    )

    # -------------------------------------------------
    # Steps
    # -------------------------------------------------

    safe_assign(df_out, step_count, {"Steps": "Steps"})

    df_out["gait_nogait_new"] = np.where(df_out["Steps"] > 0, "gait", "no-gait")

    # -------------------------------------------------
    # Predictions
    # -------------------------------------------------

    safe_assign(
        df_out,
        gait_predictions,
        {"gait_nogait": "filtered_prediction"},
    )

    safe_assign(
        df_out,
        activity_predictions,
        {"gait_posture": "filtered_prediction"},
    )

    # -------------------------------------------------
    # HR placeholder
    # -------------------------------------------------

    df_out["HR"] = np.nan

    # -------------------------------------------------
    # Wear time
    # -------------------------------------------------

    if wear_time is not None:
        df_out = df_out.merge(wear_time, how="inner", on="Timestamp")
    else:
        df_out[["WT_wrist_r", "WT_wrist_l", "WT_ankle_r", "WT_ankle_l"]] = np.nan

    # -------------------------------------------------
    # Final formatting
    # -------------------------------------------------

    df_out.replace({False: 0, True: 1}, inplace=True)

    df_out.to_csv(outcome_path, index=False)

    return df_out