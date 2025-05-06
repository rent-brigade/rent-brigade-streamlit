from supabase import create_client, Client
import streamlit as st
import pandas as pd
import folium
from folium import Choropleth
from streamlit_folium import st_folium
import altair as alt
from listing_display import create_column_config, display_gouges_table
from map_display import display_map_section
from gougers_chart import display_gougers_section

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
    
    # Load charged_gougers data
    charged_gougers = supabase.table('charged_gougers').select('name', 'date_charged').execute()
    df_charged_gougers = pd.DataFrame(charged_gougers.data)
    
    # Load and process the time series data
    gouged_by_date = supabase.table('agg_by_date').select(
        'first_gouged_price_date, gouged_listings, total_dollars_gouged, cumulative_count'
    ).execute()
    df_gouged_by_date = pd.DataFrame(gouged_by_date.data)
    df_gouged_by_date['first_gouged_price_date'] = pd.to_datetime(df_gouged_by_date['first_gouged_price_date'])
    total_gouged = df_gouged_by_date['gouged_listings'].sum()
    last_update_date = max(df_gouged_by_date['first_gouged_price_date'].max() + pd.Timedelta(days=1), pd.Timestamp.now().normalize())
    last_update_date_str = last_update_date.strftime('%m/%d/%Y')
    
    # Calculate the date 7 days before the last update
    seven_days_ago = last_update_date - pd.Timedelta(days=7)

    # ===== Header and Metrics Section =====
    # Display key metrics in a three-column layout
    st.title("Rent Gouging in Los Angeles County")
    # Get the most recent date from the time series data
    st.caption(f"Last updated: {last_update_date_str}")
    r1col1, r1col2, r1col3 = st.columns([1, 1, 1])
    
    # Total gouged listings metric
    with r1col1:
        st.metric(label="Total Gouged Listings", value='{:,}'.format(total_gouged))
    
    # 7-day trend metric
    with r1col2:
        # Calculate recent activity
        recent_gouged = df_gouged_by_date[df_gouged_by_date['first_gouged_price_date'] > seven_days_ago]
        last_seven_days = recent_gouged['gouged_listings'].sum()
        prior_to_seven_days = df_gouged_by_date[df_gouged_by_date['first_gouged_price_date'] <= seven_days_ago]
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
    
    # Create the base chart
    base = alt.Chart(df_gouged_by_date).encode(
        x=alt.X('first_gouged_price_date:T', title='Date')
    )
    
    # Create the selection interval
    nearest = alt.selection_single(
        nearest=True,
        on='mouseover',
        clear='mouseout',
        fields=['first_gouged_price_date'],
        empty='none'
    )
    
    # Create the line
    line = base.mark_line(color='#ff0000').encode(
        y=alt.Y('cumulative_count:Q', title='Total Gouged Listings')
    )
    
    # Create a transparent layer for tooltips
    tooltip_layer = base.mark_rect(
        opacity=0,
        width=1
    ).encode(
        tooltip=[
            alt.Tooltip('first_gouged_price_date:T', title='Date', format='%m/%d/%Y'),
            alt.Tooltip('gouged_listings:Q', title='New Gouges', format=',.0f'),
            alt.Tooltip('cumulative_count:Q', title='Total Gouged', format=',.0f')
        ]
    ).add_selection(nearest)
    
    # Create the rule (vertical line) that follows the mouse
    rule = base.mark_rule(color='gray').encode(
        opacity=alt.condition(nearest, alt.value(0.5), alt.value(0))
    ).transform_filter(nearest)
    
    # Create the point that follows the line
    point = base.mark_point(color='red', size=50).encode(
        y=alt.Y('cumulative_count:Q')
    ).transform_filter(nearest)
    
    # Add a text label for the point
    text = base.mark_text(
        align='left',
        baseline='middle',
        dx=7
    ).encode(
        text=alt.Text('gouged_listings:Q', format=',.0f'),
        y=alt.Y('cumulative_count:Q')
    ).transform_filter(nearest)
    
    # Combine the charts
    chart = (line + tooltip_layer + rule + point + text).properties(
        width='container'
    )
    
    # Display the chart in the first column
    st.altair_chart(chart, use_container_width=True)

    # Disable scroll zooming for the line chart to prevent accidental zooming
    st.markdown("""
        <style>
            div[data-testid="stAltairChart"] iframe {
                pointer-events: none;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # ===== Gougers Charged Section =====
    display_gougers_section(df_charged_gougers, seven_days_ago)

    # ===== Egregious Gouges Table =====
    st.header("Particularly Egregious Gouges")
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
    display_map_section(supabase)

if __name__ == "__main__":
    main()
