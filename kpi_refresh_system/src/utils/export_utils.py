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
    # Safeguard 1: Check if export_sheets is empty
    if not data_dict:
        raise ValueError("No sheets to export. 'export_sheets' is empty.")
    
    buffer = io.BytesIO()
    sheets_written = 0
    
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        # Safeguard 2: Only write non-empty sheets
        for company_name, df in data_dict.items():
            if df is None or df.empty:
                continue
                
            # Excel sheet names have a 31 character limit and certain characters are not allowed
            sheet_name = company_name[:31]
            # Replace invalid characters
            for char in ['/', '\\', '?', '*', '[', ']', ':']:
                sheet_name = sheet_name.replace(char, '_')
            
            # Write DataFrame to sheet
            try:
                # For DataFrames with MultiIndex, keep the index
                if isinstance(df.index, pd.MultiIndex):
                    df.to_excel(writer, sheet_name=sheet_name)
                else:
                    # For simple index, reset it
                    df_export = df.reset_index()
                    # Don't try to rename columns - just write as is
                    df_export.to_excel(writer, sheet_name=sheet_name, index=False)
                
                sheets_written += 1
                
                # Get the worksheet for formatting
                worksheet = writer.sheets[sheet_name]
                
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
                    
            except Exception as e:
                print(f"Error writing sheet '{sheet_name}': {e}")
                continue
        
        # Safeguard 3: At least one sheet must be written
        if sheets_written == 0:
            # Create a default sheet with message
            info_df = pd.DataFrame({
                'Message': ['No data available for export.'],
                'Reason': ['All provided DataFrames were empty or invalid.']
            })
            info_df.to_excel(writer, sheet_name='Info', index=False)
            
            # Auto-adjust column widths for info sheet
            worksheet = writer.sheets['Info']
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