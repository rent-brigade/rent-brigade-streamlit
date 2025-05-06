import streamlit as st
import pandas as pd
import altair as alt

def display_gougers_section(df_charged_gougers, seven_days_ago):
    """Display the gougers charged section of the dashboard."""
    st.header("Enforcement")
    
    # Convert date_charged to datetime if it's not already
    df_charged_gougers['date_charged'] = pd.to_datetime(df_charged_gougers['date_charged'])
    
    # Calculate metrics
    num_charged_gougers = len(df_charged_gougers)
    recent_charged = df_charged_gougers[df_charged_gougers['date_charged'] > seven_days_ago]
    num_charged_gougers_recent = len(recent_charged)
    
    if num_charged_gougers > 0:
        gougers_delta_percent = (num_charged_gougers_recent / num_charged_gougers) * 100
    else:
        gougers_delta_percent = 0
    
    # Display metrics
    r2col1, r2col2 = st.columns([1, 1])
    with r2col1:
        st.metric(
            label="Total Gougers Charged", 
            value=num_charged_gougers,
        )
        
    with r2col2:
        st.metric(
            label="Gougers Charged in Last 7 Days", 
            value=num_charged_gougers_recent,
            delta=f"{gougers_delta_percent:.1f}% increase",
            delta_color="inverse"
        )
    
    # Create timeline chart
    st.subheader("Gougers Charged Over Time")
    
    # Sort by date_charged
    df_timeline = df_charged_gougers.dropna(subset=['name', 'date_charged']).copy()
    df_timeline = df_timeline.sort_values('date_charged', ascending=True)
    
    # Create a dummy point for today
    today = pd.Timestamp.now().normalize()
    dummy_data = pd.DataFrame({
        'name': [''],
        'date_charged': [today]
    })
    
    # Create the main chart
    main_chart = alt.Chart(df_timeline).mark_circle(
        size=100,
    ).encode(   
        x=alt.X('date_charged:T', 
                axis=alt.Axis(format='%b %-d',
                             title=None)),
        y=alt.Y('name:N', 
                sort=alt.EncodingSortField('date_charged', order='ascending'),
                axis=alt.Axis(labelLimit=0,
                             labelBaseline='middle',
                             labelOffset=0,
                             title=None)),
        color=alt.value('#ff0000'),
        tooltip=[
            alt.Tooltip('name:N', title='Charged Gouger'),
            alt.Tooltip('date_charged:T', title='Date Charged', format='%B %-d, %Y')
        ]
    )
    
    # Create a dummy chart with an invisible point
    dummy_chart = alt.Chart(dummy_data).mark_point(
        opacity=0
    ).encode(
        x='date_charged:T',
        y=alt.Y('name:N', sort=alt.EncodingSortField('date_charged', order='ascending'))
    )
    
    # Create gridlines
    x_grid_data = pd.DataFrame({
        'date': pd.date_range(
            start=df_timeline['date_charged'].min(),
            end=today,
            freq='MS'
        )
    })
    
    x_grid_chart = alt.Chart(x_grid_data).mark_rule(
        color='lightgray',
        opacity=0.3
    ).encode(
        x='date:T',
        y=alt.value(0),
        y2=alt.value(250)
    )
    
    # Create y-axis gridlines
    y_grid_data = pd.DataFrame({
        'name': df_timeline['name'].unique(),
        'date_charged': [df_timeline[df_timeline['name'] == name]['date_charged'].min() for name in df_timeline['name'].unique()]
    })
    
    y_grid_chart = alt.Chart(y_grid_data).mark_rule(
        color='lightgray',
        opacity=0.2,
        strokeWidth=0.5
    ).encode(
        y=alt.Y('name:N', 
                sort=alt.EncodingSortField('date_charged', order='ascending'))
    )
    
    # Create today's line
    today_data = pd.DataFrame({
        'date': [today],
        'label': ['Today']
    })
    
    today_line = alt.Chart(today_data).mark_rule(
        color='#FFB6C1',
        strokeWidth=2
    ).encode(
        x='date:T',
        y=alt.value(0),
        y2=alt.value(250)
    )
    
    today_label = alt.Chart(today_data).mark_text(
        align='left',
        baseline='middle',
        dx=5,
        color='#FFB6C1'
    ).encode(
        x='date:T',
        y=alt.value(0),
        text='label:N'
    )
    
    # Combine all charts
    chart = (x_grid_chart + y_grid_chart + today_line + today_label + main_chart + dummy_chart).properties(
        width='container',
        height=300
    ).configure(
        axisX={
            'tickCount': 'month',
            'format': '%B',
            'labelAngle': 0,
            'labelPadding': 0,
            'grid': False,
            'labelOffset': -3.5
        }
    )
    
    st.altair_chart(chart, use_container_width=True) 