from supabase import create_client, Client
import streamlit as st
import pandas as pd
import folium
from folium import Choropleth
from streamlit_folium import st_folium
import altair as alt
from listing_display import create_column_config, display_gouges_table

# ===== Configuration =====
# These constants define the application's configuration and behavior

# Supabase Configuration
# URL for the Supabase database instance
SUPABASE_URL = "https://bntkbculofzofhwzjsps.supabase.co"

# Table Display Configuration
# Controls the visual appearance of data tables
MAX_TABLE_HEIGHT = 600  # Maximum height for tables in pixels
MIN_TABLE_HEIGHT = 200  # Minimum height for tables in pixels
ROW_HEIGHT = 42        # Approximate height per row in pixels

# Map Configuration
# Defines the settings for different geographic views
# Each entry contains:
# - table_name: The Supabase table containing the GeoJSON data
# - col_name: The display name for the region type
# - location: Default map center coordinates [latitude, longitude]
# - zoom_start: Initial zoom level for the map
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
# These functions handle specific tasks and are used throughout the application

def initialize_supabase_client():
    """Initialize and return Supabase client.
    
    Creates a connection to the Supabase database using the URL and API key.
    The API key is stored in Streamlit's secrets management.
    """
    return create_client(SUPABASE_URL, st.secrets["SUPABASE_KEY"])

@st.cache_data(show_spinner="Loading...")
def fetch_geojson_data(_supabase_client, table_name):
    """Fetch and return GeoJSON data from Supabase.
    
    Args:
        _supabase_client: The Supabase client instance (prefixed with _ to prevent caching)
        table_name: Name of the table containing the GeoJSON data
        
    Returns:
        The GeoJSON data for the specified table
    """
    response = _supabase_client.table(table_name).select("geojson").execute()
    return response.data[0]["geojson"]

def create_folium_map(location, zoom_start):
    """Create and return a configured Folium map.
    
    Args:
        location: [latitude, longitude] coordinates for the map center
        zoom_start: Initial zoom level for the map
        
    Returns:
        A configured Folium map instance
    """
    return folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles='CartoDB Positron',  # Lightweight map tiles suitable for data visualization
        control_scale=True,        # Show scale control
        zoom_control=True,         # Show zoom controls
        zoom_delta=0.5,            # Fine-grained zoom control
        max_zoom=20,               # Maximum zoom level
        min_zoom=7                 # Minimum zoom level
    )

def create_tooltip(col_name):
    """Create and return a configured GeoJsonTooltip.
    
    Args:
        col_name: The display name for the region type (e.g., "District", "City")
        
    Returns:
        A configured GeoJsonTooltip instance
    """
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
    """Prepare and return processed table data.
    
    Args:
        geojson_data: The GeoJSON data containing region information
        is_city_data: Boolean indicating if this is city-level data
        
    Returns:
        A processed DataFrame ready for display
    """
    # Convert GeoJSON features to DataFrame
    table_data = pd.DataFrame([f['properties'] for f in geojson_data['features']])
    
    # Special handling for city data
    if is_city_data:
        # Convert city names to title case
        table_data['region'] = table_data['region'].str.title()
        # Combine "Unincorporated Area" rows and sum their gouged listings
        table_data = table_data.groupby('region', as_index=False)['gouged_listings'].sum()
    
    # Sort by number of gouged listings (highest to lowest)
    table_data = table_data.sort_values('gouged_listings', ascending=False)
    return table_data

def calculate_table_height(num_rows):
    """Calculate appropriate table height based on number of rows.
    
    Args:
        num_rows: Number of rows in the table
        
    Returns:
        Height in pixels, constrained between MIN_TABLE_HEIGHT and MAX_TABLE_HEIGHT
    """
    return min(max(num_rows * ROW_HEIGHT, MIN_TABLE_HEIGHT), MAX_TABLE_HEIGHT)

# ===== Main Application =====
def main():
    """Main application function that sets up and runs the Streamlit dashboard."""
    
    # Initialize database connection and fetch initial data
    supabase = initialize_supabase_client()
    
    # Load and process the time series data
    gouged_by_date = supabase.table('agg_by_date').select(
        'first_gouged_price_date, gouged_listings, total_dollars_gouged, cumulative_count'
    ).execute()
    df_gouged_by_date = pd.DataFrame(gouged_by_date.data)
    df_gouged_by_date['first_gouged_price_date'] = pd.to_datetime(df_gouged_by_date['first_gouged_price_date'])
    total_gouged = df_gouged_by_date['gouged_listings'].sum()

    # ===== Header and Metrics Section =====
    # Display key metrics in a three-column layout
    st.title("Rent Gouging in Los Angeles County")
    r1col1, r1col2, r1col3 = st.columns([1, 1, 1])
    
    # Total gouged listings metric
    with r1col1:
        st.metric(label="Total Gouged Listings", value='${:,}'.format(total_gouged))
    
    # 7-day trend metric
    with r1col2:
        # Calculate recent activity
        recent_gouged = df_gouged_by_date.sort_values('first_gouged_price_date', ascending=False).head(7)
        last_seven_days = recent_gouged['gouged_listings'].sum()
        prior_to_seven_days = df_gouged_by_date.sort_values('first_gouged_price_date', ascending=False).iloc[7:]
        prior_to_seven_days_total = prior_to_seven_days['gouged_listings'].sum()
        delta_percent = ((total_gouged - prior_to_seven_days_total) / total_gouged) * 100 if prior_to_seven_days_total > 0 else 0
        
        st.metric(
            label="New Gouges in Last 7 Days", 
            value=last_seven_days,
            delta=f"{delta_percent:.1f}% increase",
            delta_color="inverse"
        )
    
    # Total dollars gouged metric
    with r1col3:
        total_dollars_gouged = df_gouged_by_date['total_dollars_gouged'].sum()
        st.metric(
            label="Total Dollars Gouged", 
            value='${:,.2f}MM'.format(total_dollars_gouged / 1000000),
        )

    # ===== Time Series Line Chart =====
    # Display cumulative gouged listings over time
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

    # Disable scroll zooming for the line chart to prevent accidental zooming
    st.markdown("""
        <style>
            div[data-testid="stAltairChart"] iframe {
                pointer-events: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # ===== Egregious Gouges Table =====
    st.header("Particularly Egregious Gouges 🔪")
    # Get the columns to display from the configuration
    column_config = create_column_config()
    display_columns = [col for col, config in column_config.items() if config["display"]]
    
    # Fetch the egregious gouges data from Supabase
    gouges_data = supabase.table('egregious_gouges').select(','.join(display_columns)).execute()
    df_gouges = pd.DataFrame(gouges_data.data)
    
    # Sort and display the table
    df_gouges = df_gouges.sort_values("base_vs_latest_price", ascending=False)
    display_gouges_table(df_gouges, column_config)

    # ===== Map Section =====
    # Interactive map showing gouged listings by geographic region
    st.header("Maps")
    
    # Allow user to select which geographic view to display
    selected_label = st.selectbox("View by", list(MAP_CONFIGS.keys()))
    cfg = MAP_CONFIGS[selected_label]
    
    # Fetch the appropriate GeoJSON data
    geojson_data = fetch_geojson_data(supabase, cfg["table_name"])
    
    # Create and configure the map
    m = create_folium_map(cfg["location"], cfg["zoom_start"])
    
    # Add choropleth layer to show gouged listings density
    Choropleth(
        geo_data=geojson_data,
        data=pd.DataFrame([f['properties'] for f in geojson_data['features']]),
        columns=['region', 'gouged_listings'],
        key_on="feature.properties.region",
        fill_color="OrRd",  # Orange-Red color scheme
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Ever Gouged Listings"
    ).add_to(m)

    # Add interactive tooltips to the map
    tooltip = create_tooltip(cfg["col_name"])
    folium.GeoJson(
        geojson_data,
        style_function=lambda x: {'fillOpacity': 0, 'color': 'black', 'weight': 0.5},
        tooltip=tooltip
    ).add_to(m)

    # Create two-column layout for map and data table
    r2col1, r2col2 = st.columns([2.25, 1])  # Map takes more space than table

    # Display the map
    with r2col1:
        st_folium(m, use_container_width=True, height=600)

    # Display the data table
    with r2col2:
        # Prepare and display the table data
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
