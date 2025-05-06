import streamlit as st
import pandas as pd
import folium
from folium import Choropleth
from streamlit_folium import st_folium

# Map Configuration
MAP_CONFIGS = {
    "Supervisor Districts": {
        "table_name": "supervisor_geojson",
        "col_name": "District",
        "location": [34.32, -118.26],
        "zoom_start": 9,
    },
    "Council Districts": {
        "table_name": "council_geojson",
        "col_name": "District",
        "location": [34.05, -118.4],
        "zoom_start": 10,
    },
    "ZIP Codes": {
        "table_name": "zipcode_geojson",
        "col_name": "ZIP Code",
        "location": [34.32, -118.26],
        "zoom_start": 9,
    },
    "Cities": {
        "table_name": "city_geojson",
        "col_name": "City",
        "location": [34.32, -118.26],
        "zoom_start": 9,
    }
}

@st.cache_data(show_spinner=False)
def fetch_geojson_data(_supabase_client, table_name):
    """Fetch and cache GeoJSON data from Supabase."""
    response = _supabase_client.table(table_name).select("geojson").execute()
    return response.data[0]["geojson"]

def create_folium_map(location, zoom_start):
    """Create and return a configured Folium map."""
    return folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles='CartoDB Positron',
        control_scale=True,
        zoom_control=True,
        zoom_delta=0.5,
        max_zoom=20,
        min_zoom=7
    )

def create_tooltip(col_name):
    """Create and return a configured GeoJsonTooltip."""
    return folium.GeoJsonTooltip(
        fields=['region', 'gouged_listings'],
        aliases=[col_name, 'Gouged Listings '],
        localize=True,
        sticky=True,
        labels=True,
        max_width=600,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
            padding: 8px;
            font-size: 14px;
        """
    )

def prepare_table_data(geojson_data, is_city_data=False):
    """Prepare and return processed table data."""
    table_data = pd.DataFrame([f['properties'] for f in geojson_data['features']])
    
    if is_city_data:
        table_data['region'] = table_data['region'].str.title()
        table_data = table_data.groupby('region', as_index=False)['gouged_listings'].sum()
    
    table_data = table_data.sort_values('gouged_listings', ascending=False)
    return table_data

def calculate_table_height(num_rows):
    """Calculate appropriate table height based on number of rows."""
    MIN_TABLE_HEIGHT = 200
    MAX_TABLE_HEIGHT = 600
    ROW_HEIGHT = 42
    return min(max(num_rows * ROW_HEIGHT, MIN_TABLE_HEIGHT), MAX_TABLE_HEIGHT)

@st.cache_data(show_spinner=False)
def create_map_data(_supabase_client, selected_label):
    """Create and cache map data for the selected label."""
    cfg = MAP_CONFIGS[selected_label]
    
    # Fetch the appropriate GeoJSON data
    geojson_data = fetch_geojson_data(_supabase_client, cfg["table_name"])
    
    return {
        'geojson_data': geojson_data,
        'is_city_data': cfg["table_name"] == 'city_geojson',
        'col_name': cfg["col_name"],
        'location': cfg["location"],
        'zoom_start': cfg["zoom_start"]
    }

def display_map_section(supabase_client):
    """Display the map section of the dashboard."""
    st.header("Maps")
    
    selected_label = st.selectbox("View by", list(MAP_CONFIGS.keys()))
    
    # Get cached map data
    cached_data = create_map_data(supabase_client, selected_label)
    
    # Create a new map instance
    m = create_folium_map(cached_data['location'], cached_data['zoom_start'])
    
    # Add choropleth layer
    Choropleth(
        geo_data=cached_data['geojson_data'],
        data=pd.DataFrame([f['properties'] for f in cached_data['geojson_data']['features']]),
        columns=['region', 'gouged_listings'],
        key_on="feature.properties.region",
        fill_color="OrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Ever Gouged Listings"
    ).add_to(m)

    # Add interactive tooltips
    tooltip = create_tooltip(cached_data['col_name'])
    folium.GeoJson(
        cached_data['geojson_data'],
        style_function=lambda x: {'fillOpacity': 0, 'color': 'black', 'weight': 0.5},
        tooltip=tooltip
    ).add_to(m)

    # Create two-column layout
    r3col1, r3col2 = st.columns([2, 1])

    # Display the map
    with r3col1:
        st_folium(m, use_container_width=True, height=600)

    # Display the data table
    with r3col2:
        table_data = prepare_table_data(cached_data['geojson_data'], cached_data['is_city_data'])
        dynamic_height = calculate_table_height(len(table_data))
        
        st.dataframe(
            table_data[['region', 'gouged_listings']]
            .rename(columns={
                'region': cached_data['col_name'],
                'gouged_listings': 'Gouged Listings'
            }), 
            hide_index=True,
            use_container_width=True,
            height=dynamic_height
        )