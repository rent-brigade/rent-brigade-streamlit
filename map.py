from supabase import create_client, Client
import streamlit as st
import pandas as pd
import folium
from folium import Choropleth
from streamlit_folium import st_folium
import json
import altair as alt

# Initialize Supabase client
url: str = "https://bntkbculofzofhwzjsps.supabase.co"
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Load gouged by date dataset
gouged_by_date = supabase.table('agg_by_date').select('first_gouged_price_date, gouged_listings, total_dollars_gouged, cumulative_count').execute()
# gouged_by_date = supabase.table('agg_by_date').select('*').execute()
df_gouged_by_date = pd.DataFrame(gouged_by_date.data)
df_gouged_by_date['first_gouged_price_date'] = pd.to_datetime(df_gouged_by_date['first_gouged_price_date'])
total_gouged = df_gouged_by_date['gouged_listings'].sum()

st.header("Rent Gouging in Los Angeles County")
r1col1, r1col2, r1col3 = st.columns([1, 1, 1])
with r1col1:
    
    st.metric(label="Total Gouged Listings", value='${:,}'.format(total_gouged))
    
with r1col2:
    # Calculate total listings gouged in last 7 days
    recent_gouged = df_gouged_by_date.sort_values('first_gouged_price_date', ascending=False).head(7)
    last_seven_days = recent_gouged['gouged_listings'].sum()
    
    # Calculate the sum of all other rows
    prior_to_seven_days = df_gouged_by_date.sort_values('first_gouged_price_date', ascending=False).iloc[7:]
    prior_to_seven_days_total = prior_to_seven_days['gouged_listings'].sum()
    
    # Calculate percentage change
    if prior_to_seven_days_total > 0:
        delta_percent = ((total_gouged - prior_to_seven_days_total) / total_gouged) * 100
    else:
        delta_percent = 0
    
    st.metric(
        label="Total Listings Gouged in Last 7 Days", 
        value=last_seven_days,
        delta=f"{delta_percent:.1f}% increase"
    )
    
with r1col3:
    total_dollars_gouged = df_gouged_by_date['total_dollars_gouged'].sum()
    st.metric(
        label="Total Dollars Gouged", 
        value='${:,.2f}MM'.format(total_dollars_gouged / 1000000),
    )
st.header("Rent-Gouged Listings Over Time")
st.altair_chart(
    alt.Chart(df_gouged_by_date).mark_line(color='#ff0000').encode(
        x=alt.X('first_gouged_price_date:T', title='Date'),
        y=alt.Y('cumulative_count:Q', title='Total Gouged Listings')
    ).properties(
        width='container'
    ),
    use_container_width=True
)

# Disable scroll zooming only for the line chart
st.markdown("""
    <style>
        div[data-testid="stAltairChart"] iframe {
            pointer-events: none;
        }
    </style>
""", unsafe_allow_html=True)

st.header("Maps")
# Prefetch data from Supabase
map_tables = {
    "Supervisor Districts": {
        "table_name": "supervisor_district_metrics",
        "id_field": "supervisor_district",
        "col_name": "District",
        "location": [34.32, -118.26],
        "zoom_start": 9,
        
    },
    "Council Districts": {
        "table_name": "council_district_metrics",
        "id_field": "council_district",
        "col_name": "District",
        "location": [34.05, -118.4],
        "zoom_start": 10,
    },
    "ZIP Codes": {
        "table_name": "zipcode_metrics",
        "id_field": "zipcode",
        "col_name": "ZIP Code",
        "location": [34.32, -118.26],
        "zoom_start": 9,
    },
    "Cities": {
        "table_name": "city_metrics",
        "id_field": "city",
        "col_name": "City",
        "location": [34.32, -118.26],
        "zoom_start": 9,
    }
}

# Query and cache data
@st.cache_data(show_spinner="Loading...")
def fetch_data(table_name, id_field):
    response = supabase.table(table_name).select(f"{id_field}, ever_gouged_listings, total_listings, geom").execute()
    # response = supabase.table(table_name).select("*").execute()
    map_df = pd.DataFrame(response.data)
    map_df["geometry"] = map_df["geom"]
    return map_df

# Load all map datasets at startup
map_data_sources = {name: fetch_data(cfg["table_name"], cfg["id_field"]) for name, cfg in map_tables.items()}

# Map Dataset selector
selected_label = st.selectbox("View by", list(map_tables.keys()))
cfg = map_tables[selected_label]
map_df = map_data_sources[selected_label]
id_field = cfg["id_field"]

# Build GeoJSON
features = []
for _, row in map_df.iterrows():
    district_id = row[id_field]
    features.append({
        "type": "Feature",
        "geometry": row["geometry"],
        "properties": {
            "district_id": district_id,
            "ever_gouged_listings": row["ever_gouged_listings"]
        }
    })

geojson_data = {
    "type": "FeatureCollection",
    "features": features
}

# Create folium map
m = folium.Map(
    location=cfg["location"],
    zoom_start=cfg["zoom_start"],
    tiles='CartoDB Positron',
    control_scale=True,
    zoom_control=True,
    zoom_delta=0.5,
    max_zoom=20,
    min_zoom=7
) 

# Add tooltips
tooltip = folium.GeoJsonTooltip(
    fields=['district_id', 'ever_gouged_listings'],
    aliases=[cfg["col_name"], 'Gouged Listings '],
    localize=True,
    sticky=True,
    labels=True,
    style="""
        background-color: #F0EFEF;
        border: 2px solid black;
        border-radius: 3px;
        box-shadow: 3px;
        padding: 8px;
        font-size: 14px;
    """,
    style_css="""
        .leaflet-tooltip {
            white-space: nowrap;
        }
        .leaflet-tooltip .label {
            margin-right: 10px;
            min-width: 100px;
            display: inline-block;
        }
    """
)

# Create choropleth

print("\nData Inspection:", selected_label)
print("Data types:", map_df.dtypes)
print("Null values:", map_df.isnull().sum())
print("Unique values in ever_gouged_listings:", sorted(map_df['ever_gouged_listings'].unique()))
print("Sample of data:", map_df.head())

Choropleth(
    geo_data=geojson_data,
    data=map_df,
    columns=[id_field, "ever_gouged_listings"],
    key_on="feature.properties.district_id",
    fill_color="OrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Ever Gouged Listings"
).add_to(m)

# Add tooltips to the map
folium.GeoJson(
    geojson_data,
    style_function=lambda x: {'fillOpacity': 0, 'color': 'black', 'weight': 0.5},
    tooltip=tooltip
).add_to(m)

# Create layout: map on the left, table on the right
r2col1, r2col2 = st.columns([2.25, 1])  # Wider map, narrower table

# Display map
with r2col1:
    st_data = st_folium(m, use_container_width=True, height=600)

# Display table
with r2col2:
    # Calculate dynamic height based on number of rows
    num_rows = len(map_df)
    row_height = 35  # Approximate height per row in pixels
    table_height = min(num_rows * row_height, 600)
    
    # Convert city names to title case for display
    display_df = map_df.copy()
    if id_field == 'city':
        display_df[id_field] = display_df[id_field].str.title()
    
    st.dataframe(
        display_df[[id_field, "ever_gouged_listings"]]
        .rename(columns={
            id_field: cfg["col_name"],
            "ever_gouged_listings": "Gouged Listings"
        }), 
        hide_index=True,
        use_container_width=True,
        height=table_height
    )
