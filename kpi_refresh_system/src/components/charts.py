"""
Chart components for financial data visualization
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any
from ..display_utils import sort_period, format_value


def create_line_chart(df: pd.DataFrame, x_col: str = 'Period', y_col: str = 'Value',
                     color_col: Optional[str] = None, title: str = "Financial Metrics Over Time",
                     y_label: str = "Value", period_type: str = "Quarterly") -> go.Figure:
    """
    Create a line chart for financial metrics with year separation lines
    
    Args:
        df: DataFrame with data to plot
        x_col: Column name for x-axis
        y_col: Column name for y-axis
        color_col: Column name for color grouping (optional)
        title: Chart title
        y_label: Y-axis label
        period_type: 'Annual' or 'Quarterly' for period handling
        
    Returns:
        Plotly figure
    """
    # Sort periods
    if x_col in df.columns:
        df = df.sort_values(x_col, key=lambda x: x.map(sort_period))
    
    # Create figure
    fig = go.Figure()
    
    # Add traces
    if color_col and color_col in df.columns:
        # Multiple lines (grouped by color_col)
        for group_name in df[color_col].unique():
            group_data = df[df[color_col] == group_name]
            fig.add_trace(go.Scatter(
                x=group_data[x_col],
                y=group_data[y_col],
                mode='lines+markers',
                name=group_name,
                line=dict(width=3),
                marker=dict(size=8)
            ))
    else:
        # Single line
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode='lines+markers',
            name=y_label,
            line=dict(width=3),
            marker=dict(size=8)
        ))
    
    # Add year separation lines for quarterly data
    if period_type == "Quarterly" and x_col in df.columns:
        periods = df[x_col].unique()
        year_transitions = []
        
        if len(periods) > 1:
            last_year = str(periods[0]).split('-')[1] if '-' in str(periods[0]) else None
            
            for i, period in enumerate(periods[1:], 1):
                if '-' in str(period):
                    current_year = str(period).split('-')[1]
                    if last_year and current_year != last_year:
                        year_transitions.append((i-0.5, current_year))
                        last_year = current_year
            
            # Add vertical lines for year transitions
            for position, year in year_transitions:
                fig.add_vline(
                    x=position,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=year,
                    annotation_position="top"
                )
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title=y_label,
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Format y-axis based on data type
    if 'USD' in y_label or 'mm' in y_label:
        fig.update_layout(yaxis_tickformat=",.0f")
    elif '%' in y_label or 'Percentage' in y_label:
        fig.update_layout(yaxis_tickformat=".1%")
    
    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str = 'Period', y_col: str = 'Value',
                    color_col: Optional[str] = None, title: str = "Bar Chart",
                    barmode: str = 'group') -> go.Figure:
    """
    Create a bar chart with proper formatting for growth metrics
    
    Args:
        df: DataFrame with data to plot
        x_col: Column name for x-axis
        y_col: Column name for y-axis  
        color_col: Column name for color grouping (optional)
        title: Chart title
        barmode: 'group' or 'stack'
        
    Returns:
        Plotly figure
    """
    # Sort periods
    if x_col in df.columns:
        df = df.sort_values(x_col, key=lambda x: x.map(sort_period))
    
    # Create figure
    fig = go.Figure()
    
    # Check if this is growth data
    is_growth = 'Growth' in y_col or 'growth' in title.lower() or '%' in y_col
    
    if color_col and color_col in df.columns:
        # Multiple series
        for group_name in df[color_col].unique():
            group_data = df[df[color_col] == group_name]
            
            if is_growth:
                # Color based on positive/negative for growth
                colors = ['green' if v > 0 else 'red' for v in group_data[y_col]]
            else:
                colors = None
            
            fig.add_trace(go.Bar(
                x=group_data[x_col],
                y=group_data[y_col],
                name=group_name,
                marker_color=colors,
                text=[f"{v:.1f}%" if is_growth else f"{v:,.0f}" for v in group_data[y_col]],
                textposition='auto'
            ))
    else:
        # Single series
        if is_growth:
            colors = ['green' if v > 0 else 'red' for v in df[y_col]]
        else:
            colors = 'lightblue'
        
        fig.add_trace(go.Bar(
            x=df[x_col],
            y=df[y_col],
            marker_color=colors,
            text=[f"{v:.1f}%" if is_growth else f"{v:,.0f}" for v in df[y_col]],
            textposition='auto'
        ))
    
    # Add year separation lines for quarterly data
    if 'Quarter' in title and x_col in df.columns:
        periods = df[x_col].unique()
        if len(periods) > 1:
            last_year = str(periods[0]).split('-')[1] if '-' in str(periods[0]) else None
            
            for i, period in enumerate(periods[1:], 1):
                if '-' in str(period):
                    current_year = str(period).split('-')[1]
                    if last_year and current_year != last_year:
                        fig.add_vline(
                            x=i-0.5,
                            line_dash="dot",
                            line_color="lightgray"
                        )
                        last_year = current_year
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title=y_col if not is_growth else "Growth %",
        showlegend=color_col is not None,
        barmode=barmode,
        height=400
    )
    
    if is_growth:
        fig.update_yaxes(tickformat='.1f')
    
    return fig


def create_multi_company_comparison_chart(df: pd.DataFrame, metric_name: str,
                                        period_type: str = 'Quarterly') -> go.Figure:
    """
    Create comparison chart for multiple companies
    
    Args:
        df: DataFrame with columns ['Company', 'Period', 'Value']
        metric_name: Metric name for title
        period_type: 'Annual' or 'Quarterly'
        
    Returns:
        Plotly figure
    """
    # Use the standard line chart function
    return create_line_chart(
        df,
        x_col='Period',
        y_col='Value',
        color_col='Company',
        title=f"{metric_name} - Company Comparison ({period_type})",
        y_label=metric_name,
        period_type=period_type
    )
    
    return fig


def create_growth_comparison_chart(data_dict: Dict[str, pd.DataFrame],
                                 metric_name: str,
                                 growth_type: str = 'yoy',
                                 period_type: str = 'all') -> go.Figure:
    """
    Create growth comparison chart for multiple companies
    
    Args:
        data_dict: Dict mapping company ticker to DataFrame
        metric_name: Base metric name
        growth_type: 'qoq' or 'yoy'
        period_type: 'annual', 'quarterly', or 'all'
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    for ticker, df in data_dict.items():
        # Find growth metric
        growth_idx = None
        for idx in df.index:
            if (len(idx) == 4 and idx[1] == metric_name and 
                idx[3] == f'{growth_type} growth'):
                growth_idx = idx
                break
        
        if growth_idx is None:
            continue
        
        # Get growth data
        growth_data = df.loc[growth_idx]
        
        # Filter by period type
        if period_type == 'annual':
            growth_data = growth_data[[col for col in growth_data.index if col.startswith('FY')]]
        elif period_type == 'quarterly':
            growth_data = growth_data[[col for col in growth_data.index if col.startswith('Q')]]
        
        # Remove NaN values
        growth_data = growth_data.dropna()
        
        if growth_data.empty:
            continue
        
        # Add bar trace with colors
        colors = ['green' if v > 0 else 'red' for v in growth_data.values]
        
        fig.add_trace(go.Bar(
            x=growth_data.index,
            y=growth_data.values,
            name=ticker,
            text=[f"{v:.1f}%" for v in growth_data.values],
            textposition='auto',
            hovertemplate='%{y:.1f}%<extra></extra>'
        ))
    
    # Update layout
    growth_title = 'Year over Year' if growth_type == 'yoy' else 'Quarter over Quarter'
    fig.update_layout(
        title=f"{metric_name} - {growth_title} Growth Comparison",
        xaxis_title="Period",
        yaxis_title="Growth %",
        yaxis_tickformat='.1f',
        yaxis_ticksuffix='%',
        barmode='group',
        hovermode='x unified'
    )
    
    return fig