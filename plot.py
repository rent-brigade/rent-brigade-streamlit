import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from supabase import create_client, Client

# Initialize Supabase client
url: str = "https://bntkbculofzofhwzjsps.supabase.co"
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Fetch data from Supabase
st.header("Supervisor District Metrics")
response = supabase.table('supervisor_district_metrics').select('*').execute()
supervisor_district_metrics = pd.DataFrame(response.data)
st.dataframe(supervisor_district_metrics)

st.header("Council District Metrics")
response = supabase.table('council_district_metrics').select('*').execute()
council_district_metrics = pd.DataFrame(response.data)
st.dataframe(council_district_metrics)

st.header("Ever Gouged by Supervisor District")
response = supabase.table('ever_gouged_by_supervisor_district').select('*').execute()
ever_gouged_by_supervisor_district = pd.DataFrame(response.data)
st.dataframe(ever_gouged_by_supervisor_district)

st.header("Ever Gouged by Council District")
response = supabase.table('ever_gouged_by_council_district').select('*').execute()
ever_gouged_by_council_district = pd.DataFrame(response.data)
st.dataframe(ever_gouged_by_council_district)

st.header("Ever Gouged by First Gouged Date")
response = supabase.table('ever_gouged_by_first_gouged_date').select('*').execute()
ever_gouged_by_first_gouged_date = pd.DataFrame(response.data)
st.dataframe(ever_gouged_by_first_gouged_date)

st.header("Newly Gouged in Past Week")
response = supabase.table('newly_gouged_in_past_week').select('*').execute()
newly_gouged_in_past_week = pd.DataFrame(response.data)
st.dataframe(newly_gouged_in_past_week)

st.header("Zipcode Metrics")
response = supabase.table('zipcode_metrics').select('*').execute()
zipcode_metrics = pd.DataFrame(response.data)
st.dataframe(zipcode_metrics)