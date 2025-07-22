"""
Chart components for financial data visualization
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any
from ..display_utils import sort_period, format_value


def create_line_chart(df: pd.DataFrame, title: str = "Financial Metrics Over Time",
                     show_markers: bool = True) -> go.Figure:
    """
    Create a line chart for financial metrics
    
    Args:
        df: DataFrame with metrics as rows and periods as columns
        title: Chart title
        show_markers: Whether to show markers on lines
        
    Returns:
        Plotly figure
    """
    # Prepare data for plotting
    plot_data = []
    
    for idx in df.index:
        if len(idx) == 4 and pd.isna(idx[3]):  # Base metrics only
            metric_name = idx[1]  # Description
            
            # Get values for this metric
            values = []
            periods = []
            
            for col in df.columns:
                value = df.loc[idx, col]
                if pd.notna(value):
                    values.append(value)
                    periods.append(col)
            
            if values:  # Only add if there's data
                plot_data.append({
                    'metric': metric_name,
                    'periods': periods,
                    'values': values
                })
    
    # Create figure
    fig = go.Figure()
    
    # Add traces
    for data in plot_data:
        fig.add_trace(go.Scatter(
            x=data['periods'],
            y=data['values'],
            mode='lines+markers' if show_markers else 'lines',
            name=data['metric'],
            text=[f"{v:,.0f}" for v in data['values']],
            hovertemplate='%{text}<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        title=title,
        xaxis_title="Period",
        yaxis_title="Value",
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig


def create_bar_chart(df: pd.DataFrame, metric_name: str, 
                    chart_type: str = 'values',
                    period_type: str = 'all') -> go.Figure:
    """
    Create a bar chart for a specific metric
    
    Args:
        df: DataFrame with financial data
        metric_name: Name of the metric to plot
        chart_type: 'values', 'qoq', or 'yoy'
        period_type: 'annual', 'quarterly', or 'all'
        
    Returns:
        Plotly figure
    """
    # Find the metric row
    metric_idx = None
    for idx in df.index:
        if len(idx) == 4 and idx[1] == metric_name:
            if chart_type == 'values' and pd.isna(idx[3]):
                metric_idx = idx
                break
            elif chart_type == 'qoq' and idx[3] == 'qoq growth':
                metric_idx = idx
                break
            elif chart_type == 'yoy' and idx[3] == 'yoy growth':
                metric_idx = idx
                break
    
    if metric_idx is None:
        return go.Figure().add_annotation(
            text=f"No data available for {metric_name} ({chart_type})",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Get data
    metric_data = df.loc[metric_idx]
    
    # Filter by period type
    if period_type == 'annual':
        metric_data = metric_data[[col for col in metric_data.index if col.startswith('FY')]]
    elif period_type == 'quarterly':
        metric_data = metric_data[[col for col in metric_data.index if col.startswith('Q')]]
    
    # Remove NaN values
    metric_data = metric_data.dropna()
    
    if metric_data.empty:
        return go.Figure().add_annotation(
            text=f"No data available for {metric_name}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Create bar chart
    fig = go.Figure()
    
    # Set colors based on chart type
    if chart_type in ['qoq', 'yoy']:
        colors = ['green' if v > 0 else 'red' for v in metric_data.values]
        text_template = '%{y:.1f}%'
        y_title = "Growth %"
    else:
        colors = 'lightblue'
        text_template = '%{y:,.0f}'
        y_title = "Value"
    
    fig.add_trace(go.Bar(
        x=metric_data.index,
        y=metric_data.values,
        marker_color=colors,
        text=[f"{v:.1f}%" if chart_type in ['qoq', 'yoy'] else f"{v:,.0f}" 
              for v in metric_data.values],
        textposition='auto',
        hovertemplate=text_template + '<extra></extra>'
    ))
    
    # Update layout
    title_suffix = {'qoq': ' - Quarter over Quarter Growth', 
                   'yoy': ' - Year over Year Growth'}.get(chart_type, '')
    
    fig.update_layout(
        title=f"{metric_name}{title_suffix}",
        xaxis_title="Period",
        yaxis_title=y_title,
        showlegend=False
    )
    
    if chart_type in ['qoq', 'yoy']:
        fig.update_yaxis(tickformat='.1f', ticksuffix='%')
    
    return fig


def create_multi_company_comparison_chart(data_dict: Dict[str, pd.DataFrame], 
                                        metric_name: str,
                                        chart_type: str = 'line',
                                        period_type: str = 'all') -> go.Figure:
    """
    Create comparison chart for multiple companies
    
    Args:
        data_dict: Dict mapping company ticker to DataFrame
        metric_name: Metric to compare
        chart_type: 'line' or 'bar'
        period_type: 'annual', 'quarterly', or 'all'
        
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    for ticker, df in data_dict.items():
        # Find metric in this company's data
        metric_idx = None
        for idx in df.index:
            if len(idx) == 4 and pd.isna(idx[3]) and idx[1] == metric_name:
                metric_idx = idx
                break
        
        if metric_idx is None:
            continue
        
        # Get data for this metric
        metric_data = df.loc[metric_idx]
        
        # Filter by period type
        if period_type == 'annual':
            metric_data = metric_data[[col for col in metric_data.index if col.startswith('FY')]]
        elif period_type == 'quarterly':
            metric_data = metric_data[[col for col in metric_data.index if col.startswith('Q')]]
        
        # Remove NaN values
        metric_data = metric_data.dropna()
        
        if metric_data.empty:
            continue
        
        # Add trace
        if chart_type == 'line':
            fig.add_trace(go.Scatter(
                x=metric_data.index,
                y=metric_data.values,
                mode='lines+markers',
                name=ticker,
                text=[f"{v:,.0f}" for v in metric_data.values],
                hovertemplate='%{text}<extra></extra>'
            ))
        else:  # bar
            fig.add_trace(go.Bar(
                x=metric_data.index,
                y=metric_data.values,
                name=ticker,
                text=[f"{v:,.0f}" for v in metric_data.values],
                textposition='auto',
                hovertemplate='%{y:,.0f}<extra></extra>'
            ))
    
    # Update layout
    fig.update_layout(
        title=f"{metric_name} - Company Comparison",
        xaxis_title="Period",
        yaxis_title="Value",
        hovermode='x unified',
        barmode='group' if chart_type == 'bar' else None
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