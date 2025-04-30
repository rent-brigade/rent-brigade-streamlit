from supabase import create_client, Client
import streamlit as st
import pandas as pd
import folium
from folium import Choropleth
from streamlit_folium import st_folium
import json

# Initialize Supabase client
url: str = "https://bntkbculofzofhwzjsps.supabase.co"
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Prefetch data from Supabase
tables = {
    "Supervisor Districts": {
        "table_name": "supervisor_district_metrics",
        "id_field": "supervisor_district"
    },
    "Council Districts": {
        "table_name": "council_district_metrics",
        "id_field": "council_district"
    }
}

# Query and cache data
@st.cache_data(show_spinner="Loading data from Supabase...")
def fetch_data(table_name):
    response = supabase.table(table_name).select("*").execute()
    df = pd.DataFrame(response.data)
    df["geometry"] = df["geom"]
    return df

# Load all datasets at startup
data_sources = {name: fetch_data(cfg["table_name"]) for name, cfg in tables.items()}

# UI: Dataset selector
selected_label = st.selectbox("Select a dataset", list(tables.keys()))
cfg = tables[selected_label]
df = data_sources[selected_label]
id_field = cfg["id_field"]

# Build GeoJSON
features = []
for _, row in df.iterrows():
    features.append({
        "type": "Feature",
        "geometry": row["geometry"],
        "properties": {
            "district_id": row[id_field],
            "ever_gouged_listings": row["ever_gouged_listings"]
        }
    })

geojson_data = {
    "type": "FeatureCollection",
    "features": features
}

# Create folium map
m = folium.Map(location=[34.0, -118.3], zoom_start=9, tiles='CartoDB positron')  # Adjust center/zoom as needed

Choropleth(
    geo_data=geojson_data,
    data=df,
    columns=[id_field, "ever_gouged_listings"],
    key_on="feature.properties.district_id",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Ever Gouged Listings"
).add_to(m)

# Display map
st_data = st_folium(m, width=700, height=500)

# Fetch data from Supabase
st.dataframe(df)
