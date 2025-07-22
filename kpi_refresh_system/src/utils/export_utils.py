import io
import pandas as pd
from typing import Dict, Tuple

def to_excel_multi_sheets(data_dict: Dict[str, pd.DataFrame], file_name: str) -> Tuple[bytes, str]:
    """
    Export multiple DataFrames to Excel with one sheet per company.
    
    Args:
        data_dict: Dictionary mapping company names to DataFrames
        file_name: Suggested filename for download
        
    Returns:
        Tuple of (excel_bytes, suggested_filename)
    """
    buffer = io.BytesIO()
    
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for company_name, df in data_dict.items():
            # Excel sheet names have a 31 character limit and certain characters are not allowed
            sheet_name = company_name[:31]
            # Replace invalid characters
            for char in ['/', '\\', '?', '*', '[', ']', ':']:
                sheet_name = sheet_name.replace(char, '_')
            
            # Reset index to make the metric name a regular column
            df_export = df.reset_index()
            # Rename the index column to empty string for cleaner look
            df_export.columns = [''] + list(df.columns)
            
            # Write DataFrame to sheet without index
            df_export.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Get the worksheet for formatting
            worksheet = writer.sheets[sheet_name]
            
            # Apply formatting
            from openpyxl.styles import numbers
            
            # Format cells - start from row 2 (after header)
            for row_idx, row in enumerate(df_export.itertuples(index=False), start=2):
                metric_name = row[0]  # First column is the metric name
                
                # Format data columns (skip first column which is metric name)
                for col_idx, value in enumerate(row[1:], start=2):  # Start from column B
                    cell = worksheet.cell(row=row_idx, column=col_idx)
                    
                    if pd.notna(value) and isinstance(value, (int, float)):
                        if "growth" in str(metric_name).lower():
                            # Format as percentage with 1 decimal
                            cell.number_format = '0.0%'
                            cell.value = value / 100  # Convert to percentage
                        else:
                            # Format as number with comma separator
                            cell.number_format = '#,##0'
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    buffer.seek(0)
    return buffer.getvalue(), file_name