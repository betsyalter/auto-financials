"""
Utility functions for display formatting and common operations
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Tuple, Optional, Any

def sort_period(period: str) -> int:
    """
    Sort function for financial periods
    
    Args:
        period: Period string like 'FY20', 'Q1-20'
    
    Returns:
        Sort key as integer
    """
    if period.startswith('FY'):
        # FY20, FY21, etc.
        return int(period[2:])
    elif period.startswith('Q'):
        # Q1-20, Q2-21, etc.
        parts = period.split('-')
        quarter = int(parts[0][1])
        year = int(parts[1])
        return year * 10 + quarter
    return 0

def format_value(value: float, is_growth: bool = False, needs_mm: bool = False) -> str:
    """
    Format a numeric value for display
    
    Args:
        value: The numeric value to format
        is_growth: Whether this is a growth percentage
        needs_mm: Whether this value needs to be shown in millions
    
    Returns:
        Formatted string
    """
    if pd.isna(value):
        return ""
    
    if is_growth:
        return f"{value:.1f}%"
    elif needs_mm:
        # Format in millions with appropriate decimal places
        value_in_mm = value / 1000000
        if abs(value_in_mm) < 1:
            # For values less than 1 million, show 3 decimal places
            return f"{value_in_mm:,.3f}"
        elif abs(value_in_mm) < 10:
            # For values 1-10 million, show 1 decimal place
            return f"{value_in_mm:,.1f}"
        else:
            # For values >= 10 million, show no decimal places
            return f"{value_in_mm:,.0f}"
    else:
        return f"{value:,.0f}"

def check_needs_mm(values: pd.Series) -> bool:
    """
    Check if a series of values needs to be displayed in millions
    
    Args:
        values: Pandas series of numeric values
    
    Returns:
        True if any value >= 1 million
    """
    return any(abs(val) >= 1000000 for val in values if pd.notna(val))

def add_mm_suffix(description: str, needs_mm: bool) -> str:
    """
    Add ', mm' suffix to description if needed
    
    Args:
        description: The metric description
        needs_mm: Whether to add the suffix
    
    Returns:
        Description with or without suffix
    """
    if needs_mm and ", mm" not in description:
        return f"{description}, mm"
    return description

def create_line_chart(chart_data: pd.DataFrame, 
                     x_col: str, 
                     y_col: str, 
                     color_col: str,
                     title: str,
                     y_label: str = "Value",
                     period_type: str = "Quarterly") -> go.Figure:
    """
    Create a standardized line chart with proper period sorting
    
    Args:
        chart_data: DataFrame with chart data
        x_col: Column name for x-axis (periods)
        y_col: Column name for y-axis (values)
        color_col: Column name for color grouping
        title: Chart title
        y_label: Y-axis label
        period_type: "Quarterly" or "Annual"
    
    Returns:
        Plotly figure object
    """
    # Sort periods chronologically
    unique_periods = list(chart_data[x_col].unique())
    unique_periods = sorted(unique_periods, key=sort_period)
    chart_data[x_col] = pd.Categorical(chart_data[x_col], categories=unique_periods, ordered=True)
    
    # Create line chart
    fig = px.line(chart_data, x=x_col, y=y_col, color=color_col,
                  title=title, markers=True)
    
    # Update layout
    fig.update_layout(
        xaxis_title="Period",
        yaxis_title=y_label,
        hovermode='x unified',
        height=500
    )
    
    # Add year separators for quarterly view
    if period_type == "Quarterly" and len(unique_periods) > 0:
        year_transitions = []
        last_year = unique_periods[0].split('-')[1]
        
        for i, period in enumerate(unique_periods[1:], 1):
            curr_year = period.split('-')[1]
            if curr_year != last_year:
                year_transitions.append(i - 0.5)
                last_year = curr_year
        
        # Add vertical lines at year transitions
        for x_pos in year_transitions:
            fig.add_vline(x=x_pos, line_dash="dash", line_color="gray", opacity=0.5)
    
    return fig

def create_bar_chart(chart_data: pd.DataFrame,
                    x_col: str,
                    y_col: str,
                    color_col: str,
                    title: str,
                    barmode: str = 'group') -> go.Figure:
    """
    Create a standardized bar chart with proper period sorting
    
    Args:
        chart_data: DataFrame with chart data
        x_col: Column name for x-axis (periods)
        y_col: Column name for y-axis (values)
        color_col: Column name for color grouping
        title: Chart title
        barmode: 'group' or 'stack'
    
    Returns:
        Plotly figure object
    """
    # Sort periods chronologically
    unique_periods = list(chart_data[x_col].unique())
    unique_periods = sorted(unique_periods, key=sort_period)
    chart_data[x_col] = pd.Categorical(chart_data[x_col], categories=unique_periods, ordered=True)
    
    fig = px.bar(chart_data, x=x_col, y=y_col, color=color_col,
                 title=title, barmode=barmode)
    
    fig.update_layout(yaxis_tickformat=".1f")
    
    # Add year separators for quarterly data
    if any(p.startswith('Q') for p in unique_periods):
        year_transitions = []
        last_year = unique_periods[0].split('-')[1] if '-' in unique_periods[0] else None
        
        for i, period in enumerate(unique_periods[1:], 1):
            if '-' in period:
                curr_year = period.split('-')[1]
                if curr_year != last_year:
                    year_transitions.append(i - 0.5)
                    last_year = curr_year
        
        for x_pos in year_transitions:
            fig.add_vline(x=x_pos, line_dash="dash", line_color="gray", opacity=0.5)
    
    return fig

def format_dataframe_for_display(df: pd.DataFrame, 
                               include_growth: Dict[str, bool] = None) -> pd.DataFrame:
    """
    Format a dataframe for display with proper number formatting
    
    Args:
        df: DataFrame with financial data
        include_growth: Dict with 'qoq' and 'yoy' keys indicating which growth metrics to include
    
    Returns:
        Formatted DataFrame ready for display
    """
    if include_growth is None:
        include_growth = {'qoq': True, 'yoy': True}
    
    # Filter rows based on growth preferences
    if not include_growth.get('qoq', True) or not include_growth.get('yoy', True):
        indices_to_keep = []
        for idx in df.index:
            if isinstance(idx, tuple) and len(idx) == 4:
                if pd.isna(idx[3]):  # Base metric
                    indices_to_keep.append(idx)
                elif idx[3] == 'qoq growth' and include_growth.get('qoq', True):
                    indices_to_keep.append(idx)
                elif idx[3] == 'yoy growth' and include_growth.get('yoy', True):
                    indices_to_keep.append(idx)
            else:
                indices_to_keep.append(idx)
        
        df = df.loc[indices_to_keep]
    
    # Check which rows need mm suffix
    needs_mm = {}
    for idx in df.index:
        if isinstance(idx, tuple) and len(idx) == 4 and pd.isna(idx[3]):
            row_values = df.loc[idx]
            needs_mm[idx] = check_needs_mm(row_values)
    
    # Create formatted copy
    formatted_data = {}
    for col in df.columns:
        formatted_col = []
        for idx, val in zip(df.index, df[col]):
            if pd.isna(val):
                formatted_col.append("")
            elif isinstance(idx, tuple) and len(idx) == 4 and pd.notna(idx[3]) and 'growth' in idx[3]:
                formatted_col.append(format_value(val, is_growth=True))
            else:
                # Check if this is a base metric that needs mm
                base_idx = idx if (isinstance(idx, tuple) and len(idx) == 4 and pd.isna(idx[3])) else None
                if isinstance(idx, tuple) and len(idx) == 4 and pd.notna(idx[3]):
                    # This is a growth metric, find its base
                    base_idx = idx[:-1] + (pd.NA,)
                
                needs_mm_value = needs_mm.get(base_idx, False) if base_idx else False
                formatted_col.append(format_value(val, needs_mm=needs_mm_value))
        
        formatted_data[col] = formatted_col
    
    return pd.DataFrame(formatted_data, index=df.index)

def create_period_columns(periods: List[str], period_type: str = "all") -> List[str]:
    """
    Filter and sort period columns
    
    Args:
        periods: List of all period strings
        period_type: "all", "annual", or "quarterly"
    
    Returns:
        Filtered and sorted list of periods
    """
    if period_type == "annual":
        filtered = [p for p in periods if p.startswith('FY')]
    elif period_type == "quarterly":
        filtered = [p for p in periods if p.startswith('Q')]
    else:
        filtered = periods
    
    return sorted(filtered, key=sort_period)