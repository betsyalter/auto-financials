"""
Table components and formatting utilities
"""
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from ..display_utils import format_dataframe_for_display


def prepare_display_dataframe(df: pd.DataFrame, 
                            selected_metrics: List[Tuple],
                            show_qoq: bool = True,
                            show_yoy: bool = True) -> pd.DataFrame:
    """
    Prepare DataFrame for display with selected metrics and growth options
    
    Args:
        df: Full DataFrame with all metrics
        selected_metrics: List of metric indices to display
        show_qoq: Whether to show QoQ growth
        show_yoy: Whether to show YoY growth
        
    Returns:
        Filtered and formatted DataFrame
    """
    if not selected_metrics:
        return pd.DataFrame()
    
    # Build list of indices to keep
    indices_to_keep = []
    for idx in selected_metrics:
        indices_to_keep.append(idx)  # Base metric
        
        # Add growth metrics based on selection
        if show_qoq:
            qoq_idx = idx[:-1] + ('qoq growth',)
            if qoq_idx in df.index:
                indices_to_keep.append(qoq_idx)
        
        if show_yoy:
            yoy_idx = idx[:-1] + ('yoy growth',)
            if yoy_idx in df.index:
                indices_to_keep.append(yoy_idx)
    
    # Filter dataframe
    display_df = df.loc[indices_to_keep]
    
    return display_df


def add_mm_suffix_to_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ', mm' suffix to metric names that have values >= 1M
    
    Args:
        df: DataFrame with financial data
        
    Returns:
        DataFrame with updated index
    """
    # Check which rows need ", mm" suffix
    needs_mm = {}
    for idx in df.index:
        if len(idx) == 4 and pd.isna(idx[3]):  # Base row only
            row_values = df.loc[idx]
            # Check if any value in this row is >= 1M
            needs_mm[idx] = any(abs(val) >= 1000000 for val in row_values if pd.notna(val))
    
    # Create new index with mm suffix where needed
    new_multiindex = []
    for idx in df.index:
        if len(idx) == 4:
            # For base metrics
            if pd.isna(idx[3]) and needs_mm.get(idx, False) and ", mm" not in idx[1]:
                new_idx = (idx[0], f"{idx[1]}, mm", idx[2], idx[3])
            # For growth rows, check if base needs mm
            elif pd.notna(idx[3]):
                base_idx = idx[:-1] + (pd.NA,)
                if needs_mm.get(base_idx, False) and ", mm" not in idx[1]:
                    new_idx = (idx[0], f"{idx[1]}, mm", idx[2], idx[3])
                else:
                    new_idx = idx
            else:
                new_idx = idx
            new_multiindex.append(new_idx)
        else:
            new_multiindex.append(idx)
    
    # Create copy with new index
    df_copy = df.copy()
    df_copy.index = pd.MultiIndex.from_tuples(new_multiindex)
    
    return df_copy


def simplify_index_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simplify multi-level index to single level for display
    
    Args:
        df: DataFrame with multi-level index
        
    Returns:
        DataFrame with simplified index
    """
    # Create new single-level index
    new_index = []
    for idx in df.index:
        if len(idx) == 4 and pd.isna(idx[3]):
            # Base row: show description only
            new_index.append(idx[1])
        elif len(idx) == 4 and pd.notna(idx[3]):
            # Growth row: show description + growth type
            new_index.append(f"{idx[1]} - {idx[3]}")
        else:
            # Fallback
            new_index.append(str(idx))
    
    # Handle duplicates
    if len(new_index) != len(set(new_index)):
        seen = {}
        unique_index = []
        for idx in new_index:
            if idx in seen:
                seen[idx] += 1
                unique_index.append(f"{idx} ({seen[idx]})")
            else:
                seen[idx] = 0
                unique_index.append(idx)
        new_index = unique_index
    
    # Create copy with new index
    df_copy = df.copy()
    df_copy.index = new_index
    
    return df_copy


def format_table_for_display(df: pd.DataFrame,
                           show_qoq: bool = True,
                           show_yoy: bool = True) -> pd.DataFrame:
    """
    Complete table formatting pipeline
    
    Args:
        df: Raw DataFrame
        show_qoq: Whether to include QoQ growth
        show_yoy: Whether to include YoY growth
        
    Returns:
        Formatted DataFrame ready for display
    """
    # Add mm suffix where needed
    df_with_suffix = add_mm_suffix_to_index(df)
    
    # Format values using utility function
    formatted_df = format_dataframe_for_display(
        df_with_suffix,
        include_growth={'qoq': show_qoq, 'yoy': show_yoy}
    )
    
    # Simplify index
    final_df = simplify_index_for_display(formatted_df)
    
    # Ensure unique index and columns
    if not final_df.index.is_unique:
        final_df = final_df.reset_index(drop=True)
    
    if not final_df.columns.is_unique:
        final_df.columns = pd.io.parsers.base.ParserBase(
            {'names': final_df.columns}
        )._maybe_dedup_names(final_df.columns)
    
    return final_df


def create_metric_selection_df(available_metrics: List[Dict], 
                             selected_indices: Set[int]) -> pd.DataFrame:
    """
    Create DataFrame for metric selection display
    
    Args:
        available_metrics: List of available metric dicts
        selected_indices: Set of selected metric indices
        
    Returns:
        DataFrame with selection info
    """
    data = []
    for i, metric in enumerate(available_metrics):
        data.append({
            'Selected': '✓' if i in selected_indices else '',
            'Metric': metric['description'],
            'Category': metric['category']['description'],
            'Unit': metric['unit']['description']
        })
    
    return pd.DataFrame(data)


def create_company_comparison_table(data_dict: Dict[str, pd.DataFrame],
                                  metric_groups: List[Dict],
                                  period_filter: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Create comparison table for multiple companies
    
    Args:
        data_dict: Dict mapping ticker to DataFrame
        metric_groups: List of metric groups to compare
        period_filter: Optional list of periods to include
        
    Returns:
        Comparison DataFrame
    """
    comparison_data = []
    
    for group in metric_groups:
        for ticker, metrics in group['metrics'].items():
            if ticker not in data_dict:
                continue
                
            df = data_dict[ticker]
            
            for metric in metrics:
                metric_name = metric['description']
                
                # Find metric in DataFrame
                metric_idx = None
                for idx in df.index:
                    if len(idx) == 4 and pd.isna(idx[3]) and idx[1] == metric_name:
                        metric_idx = idx
                        break
                
                if metric_idx is None:
                    continue
                
                # Get values
                metric_data = df.loc[metric_idx]
                
                # Apply period filter if provided
                if period_filter:
                    metric_data = metric_data[period_filter]
                
                # Create row
                row = {
                    'Company': ticker,
                    'Metric': metric_name,
                    'Group': group['name']
                }
                
                # Add period values
                for period in metric_data.index:
                    if pd.notna(metric_data[period]):
                        row[period] = metric_data[period]
                
                comparison_data.append(row)
    
    if not comparison_data:
        return pd.DataFrame()
    
    # Create DataFrame and pivot
    comparison_df = pd.DataFrame(comparison_data)
    
    # Set multi-index for better organization
    if 'Group' in comparison_df.columns:
        comparison_df = comparison_df.set_index(['Group', 'Company', 'Metric'])
    
    return comparison_df


def prepare_excel_export_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare data for Excel export with clean formatting
    
    Args:
        df: DataFrame to export
        
    Returns:
        Cleaned DataFrame for Excel
    """
    # Create copy
    excel_df = df.copy()
    
    # Simplify index if multi-level
    if isinstance(excel_df.index, pd.MultiIndex):
        new_index = []
        for idx in excel_df.index:
            if len(idx) == 4 and pd.isna(idx[3]):
                new_index.append(idx[1])  # Just description
            elif len(idx) == 4 and pd.notna(idx[3]):
                new_index.append(f"{idx[1]} - {idx[3]}")  # Description + growth type
            else:
                new_index.append(str(idx))
        excel_df.index = new_index
    
    return excel_df