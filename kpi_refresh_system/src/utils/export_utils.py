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
            
            # Write DataFrame to sheet
            df.to_excel(writer, sheet_name=sheet_name, index=True)
            
            # Auto-adjust column widths using openpyxl
            worksheet = writer.sheets[sheet_name]
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