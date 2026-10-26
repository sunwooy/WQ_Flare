import os
from datetime import datetime, timedelta, timezone
import pandas as pd
import io
import requests

# Dir to CSV with column "PLD_id"
PLD_list_dir = r"https://raw.githubusercontent.com/sunwooy/WQ_Flare/refs/heads/main/Data/reservoir_PLD_list.csv"

# Dir for output
output_dir = "/app/output"
os.makedirs(output_dir, exist_ok=True)

# output_file = os.path.join(output_dir, "PLD_TS.csv")




# Start and End Date of Interest. End date is when code run occu
date1 = "2023-07-25" # SWOT Science Orbit start
date2 = datetime.now(timezone.utc).strftime("%Y-%m-%d")



base_date = datetime(2000, 1, 1)


# Variables of interest
swot_vars = (
'lake_id,time,wse,wse_u,wse_r_u,wse_std,area_total,area_tot_u,area_detct,area_det_u,'
'layovr_val,xtrk_dist,quality_f,qual_f_b,dark_frac,ice_clim_f,ice_dyn_f,partial_f,xovr_cal_q,'
'geoid_hght,solid_tide,load_tidef,load_tideg,pole_tide,crid'
)

PLD = pd.read_csv(PLD_list_dir)
id_list = PLD['PLD_id']

output_file = os.path.join(output_dir, "PLD_TS.csv")
swot_out = output_file
swot_df = None

for PLD_id in id_list:
    api_url = (
        # By leaving out collection name, it automatically populates most recent version
        f'https://soto.podaac.earthdatacloud.nasa.gov/hydrocron/v1/'
        f'timeseries?feature=PriorLake&feature_id={PLD_id}'
        f'&output=csv&start_time={date1}T00:00:00Z&'
        f'end_time={date2}T23:59:59Z'
        f'&fields={swot_vars}'
    )

    try:
        response = requests.get(api_url).json()
        if 'error' in response:
            print(f"Error in {PLD_id}: {response['error']}")
            continue

        if response.get('status') == '200 OK':
            csv_str = response['results']['csv']
            df = pd.read_csv(io.StringIO(csv_str))

            # Drop negative times
            df = df[df['time'] >= 0]

            if df.empty:
                continue

            # Drop unit columns
            df = df[df.columns.drop(list(df.filter(like='units')))]

            # Convert time column
            df['time'] = df['time'].apply(lambda x: base_date + timedelta(seconds=x))
            df["time"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            df = df.drop_duplicates(subset=["lake_id", "time", "wse", "crid"], keep="first")

            # Filter 
            df = df[df["wse_u"] < 1.3]

            # Convert SWOT observed WSE to pressure transducer elevation
            offset = PLD.loc[PLD["PLD_id"] == PLD_id, "Offset_for_PT"].iloc[0]
            df["observation"] = df["wse"] - offset

            # Add site
            df["site_id"] = PLD.loc[PLD["PLD_id"] == PLD_id, "site"].iloc[0]

            # Append to swot_df -> if it's first df, then start df
            swot_df = pd.concat([swot_df, df], ignore_index=True) if swot_df is not None else df.copy()

    except Exception as e:
        print(f"Failed to process reach {PLD_id}: {e}")

if swot_df is not None and not swot_df.empty:
    # Organize into proper FLARE format
    swot_df = swot_df.rename(columns={"time": "datetime"})
    swot_df["variable"] = "elevation_m"
    swot_df["depth"] = pd.NA
    swot_df = swot_df[["site_id", "observation", "variable", "depth", "datetime"]]
    swot_df.to_csv(swot_out, index=False)

else:
    raise RuntimeError("No valid Hydrocron data downloaded")

