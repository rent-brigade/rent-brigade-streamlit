from supabase import create_client, Client
import streamlit as st
import pandas as pd
import folium
from folium import Choropleth
from streamlit_folium import st_folium
import altair as alt

# ===== Configuration =====
# Supabase Configuration
SUPABASE_URL = "https://bntkbculofzofhwzjsps.supabase.co"

# Table Display Configuration
MAX_TABLE_HEIGHT = 600  # Maximum height for tables in pixels
MIN_TABLE_HEIGHT = 200  # Minimum height for tables in pixels
ROW_HEIGHT = 42        # Approximate height per row in pixels

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

# ===== Helper Functions =====
def initialize_supabase_client():
    """Initialize and return Supabase client."""
    return create_client(SUPABASE_URL, st.secrets["SUPABASE_KEY"])

@st.cache_data(show_spinner="Loading...")
def fetch_geojson_data(_supabase_client, table_name):
    """Fetch and return GeoJSON data from Supabase."""
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
    return min(max(num_rows * ROW_HEIGHT, MIN_TABLE_HEIGHT), MAX_TABLE_HEIGHT)

# ===== Main Application =====
def main():
    # Initialize clients and fetch data
    supabase = initialize_supabase_client()
    
    # Load gouged by date dataset
    gouged_by_date = supabase.table('agg_by_date').select('first_gouged_price_date, gouged_listings, total_dollars_gouged, cumulative_count').execute()
    df_gouged_by_date = pd.DataFrame(gouged_by_date.data)
    df_gouged_by_date['first_gouged_price_date'] = pd.to_datetime(df_gouged_by_date['first_gouged_price_date'])
    total_gouged = df_gouged_by_date['gouged_listings'].sum()

    # ===== Header and Metrics =====
    st.header("Rent Gouging in Los Angeles County")
    r1col1, r1col2, r1col3 = st.columns([1, 1, 1])
    
    with r1col1:
        st.metric(label="Total Gouged Listings", value='${:,}'.format(total_gouged))
    
    with r1col2:
        recent_gouged = df_gouged_by_date.sort_values('first_gouged_price_date', ascending=False).head(7)
        last_seven_days = recent_gouged['gouged_listings'].sum()
        prior_to_seven_days = df_gouged_by_date.sort_values('first_gouged_price_date', ascending=False).iloc[7:]
        prior_to_seven_days_total = prior_to_seven_days['gouged_listings'].sum()
        delta_percent = ((total_gouged - prior_to_seven_days_total) / total_gouged) * 100 if prior_to_seven_days_total > 0 else 0
        
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

    # ===== Time Series Line Chart =====
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

    # Disable scroll zooming for the line chart
    st.markdown("""
        <style>
            div[data-testid="stAltairChart"] iframe {
                pointer-events: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # ===== Map Section =====
    st.header("Maps")
    
    # Map Dataset selector
    selected_label = st.selectbox("View by", list(MAP_CONFIGS.keys()))
    cfg = MAP_CONFIGS[selected_label]
    
    # Fetch and process map data
    geojson_data = fetch_geojson_data(supabase, cfg["table_name"])
    
    # Create and configure map
    m = create_folium_map(cfg["location"], cfg["zoom_start"])
    
    # Add choropleth
    Choropleth(
        geo_data=geojson_data,
        data=pd.DataFrame([f['properties'] for f in geojson_data['features']]),
        columns=['region', 'gouged_listings'],
        key_on="feature.properties.region",
        fill_color="OrRd",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Ever Gouged Listings"
    ).add_to(m)

    # Add tooltips
    tooltip = create_tooltip(cfg["col_name"])
    folium.GeoJson(
        geojson_data,
        style_function=lambda x: {'fillOpacity': 0, 'color': 'black', 'weight': 0.5},
        tooltip=tooltip
    ).add_to(m)

    # Create layout: map on the left, table on the right
    r2col1, r2col2 = st.columns([2.25, 1])

    # Display map
    with r2col1:
        st_folium(m, use_container_width=True, height=600)

    # Display table
    with r2col2:
        table_data = prepare_table_data(geojson_data, cfg["table_name"] == 'city_geojson')
        dynamic_height = calculate_table_height(len(table_data))
        
        st.dataframe(
            table_data[['region', 'gouged_listings']]
            .rename(columns={
                'region': cfg["col_name"],
                'gouged_listings': 'Gouged Listings'
            }), 
            hide_index=True,
            use_container_width=True,
            height=dynamic_height
        )

if __name__ == "__main__":
    main()
