import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta, datetime

# read in data (for now)
dat = pd.read_csv("gouged_only_20250423_204640.csv")

### Line chart
# 1) create a time series (weekly)
date_format = "%Y-%m-%d"
dat["first_gouged_price_date"] = dat["first_gouged_price_date"].apply(lambda x: datetime.strptime(x, date_format))
start_dt = dat["first_gouged_price_date"].min()
end_dt = dat["first_gouged_price_date"].max()

ref_dates = pd.date_range(start_dt,end_dt-timedelta(days=1))


# 2) get the count of listings that fall into "gouged"
chart_dat = pd.DataFrame(index=ref_dates, columns=["gouged_count"])
gouged_counts_by_day = []

for idx, row in chart_dat.iterrows():
    gouged_counts_by_day.append(dat.loc[dat["first_gouged_price_date"] <= idx].shape[0])

chart_dat["gouged_count"] = gouged_counts_by_day

# 3)

st.line_chart(chart_dat)