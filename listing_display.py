import streamlit as st
import pandas as pd
from typing import Dict, TypedDict

class ColumnConfig(TypedDict):
    name: str
    display: bool
    is_link: bool
    format_type: str  # 'date', 'percent', 'currency', or 'text'
    width: str  # 'small', 'medium', 'large', or None

def create_column_config() -> Dict[str, ColumnConfig]:
    """Create configuration for dataframe columns."""
    return {
        "listing_url": {
            "name": "Link", 
            "display": True, 
            "is_link": True, 
            "format_type": "link",
            "width": None
        },
        "address": {
            "name": "Address", 
            "display": True, 
            "is_link": False, 
            "format_type": "text",
            "width": None
        },
        "zipcode": {
            "name": "Zip Code", 
            "display": False, 
            "is_link": False, 
            "format_type": "text",
            "width": None
        },
        "city": {
            "name": "City", 
            "display": True, 
            "is_link": False, 
            "format_type": "text",
            "width": None
        },
        "bedrooms": {
            "name": "Type", 
            "display": True, 
            "is_link": False, 
            "format_type": "text",
            "width": None
        },
        "home_type": {
            "name": "Home Type", 
            "display": False, 
            "is_link": False, 
            "format_type": "text",
            "width": None
        },
        "fair_market_rent": {
            "name": "Fair Market Rent", 
            "display": False, 
            "is_link": False, 
            "format_type": "currency",
            "width": None
        },
        "base_price": {
            "name": "Base Price", 
            "display": True, 
            "is_link": False, 
            "format_type": "currency",
            "width": None
        },
        "max_legal_rent": {
            "name": "Max Legal Rent", 
            "display": False, 
            "is_link": False, 
            "format_type": "currency",
            "width": None
        },
        "base_price_date": {
            "name": "Base Price Date", 
            "display": False, 
            "is_link": False, 
            "format_type": "date",
            "width": None
        },
        "emergency_peak_price": {
            "name": "Emergency Peak Price", 
            "display": False, 
            "is_link": False, 
            "format_type": "currency",
            "width": None
        },
        "emergency_peak_price_date": {
            "name": "Emergency Peak Price Date", 
            "display": False, 
            "is_link": False, 
            "format_type": "date",
            "width": None
        },
        "latest_price": {
            "name": "Price",         
            "display": True, 
            "is_link": False, 
            "format_type": "currency",
            "width": None
        },
        "latest_price_date": {
            "name": "Latest Price Date", 
            "display": False, 
            "is_link": False, 
            "format_type": "date",
            "width": None
        },
        "peak_price_vs_fmr": {
            "name": "Peak Price vs FMR", 
            "display": False, 
            "is_link": False, 
            "format_type": "percent",
            "width": None
        },
        "base_vs_peak_price": {
            "name": "Base vs Peak Price", 
            "display": False, 
            "is_link": False, 
            "format_type": "percent",
            "width": None
        },
        "base_vs_latest_price": {
            "name": "% Increase",             
            "display": True, 
            "is_link": False, 
            "format_type": "percent",
            "width": None
        },
        "first_gouged_price": {
            "name": "First Gouged Price", 
            "display": False, 
            "is_link": False, 
            "format_type": "currency",
            "width": None
        },
        "first_gouged_date": {
            "name": "First Gouged Date",             
            "display": False, 
            "is_link": False, 
            "format_type": "date",
            "width": None
        }
    }

def format_value(value, format_type: str, column_name: str = None):
    """Format a value according to its type."""
    if pd.isna(value):
        return value
    
    if format_type == "date":
        try:
            # Convert to datetime and format as date only
            return pd.to_datetime(value).strftime('%Y-%m-%d')
        except:
            return value
    elif format_type == "percent":
        try:
            # Convert to percentage with no decimal places (multiply by 100)
            return f"{float(value) * 100:.0f}%"
        except:
            return value
    elif format_type == "currency":
        try:
            # Format as currency with commas
            return f"${float(value):,.0f}"
        except:
            return value
    elif format_type == "text":
        # Special handling for bedrooms column
        if column_name == "bedrooms":
            return f"{int(value)}BR" if pd.notna(value) else value
        # Convert text to title case
        return str(value).title()
    return value

def display_gouges_table(df: pd.DataFrame, column_config: Dict[str, ColumnConfig]):
    """Display the gouges data in a Streamlit dataframe with configured columns."""
    # Filter columns based on display configuration
    display_columns = [col for col, config in column_config.items() if config["display"]]
    df_display = df[display_columns].copy()
    
    # Combine address and city
    df_display["address"] = df_display["address"].str.lower().str.title() + ", " + df_display["city"].str.lower().str.title()
    
    # Remove city column since it's now part of address
    if "city" in df_display.columns:
        df_display = df_display.drop(columns=["city"])
    
    # Apply formatting to each column
    for col in df_display.columns:
        config = column_config[col]
        # Apply formatting to all columns except link type
        if config["format_type"] != "link":
            df_display[col] = df_display[col].apply(lambda x: format_value(x, config["format_type"], col))
    
    # Create column configuration for st.dataframe
    st_column_config = {}
    for col in df_display.columns:
        config = column_config[col]
        if config["is_link"]:
            st_column_config[col] = st.column_config.LinkColumn(
                config["name"],
                width=config["width"],
                display_text="🔗"  # Show link icon instead of URL
            )
        elif col == "base_vs_latest_price":
            st_column_config[col] = st.column_config.ProgressColumn(
                config["name"],
                width=config["width"],
                min_value=0,
                max_value=200,  # Cap at 200% for visualization
                format="%.0f%%",
                help="Percentage increase from base price to latest price"
            )
        else:
            st_column_config[col] = st.column_config.TextColumn(
                config["name"],
                width=config["width"]
            )
    
    # Display the dataframe
    st.dataframe(
        df_display,
        column_config=st_column_config,
        hide_index=True,
        use_container_width=True
    ) 