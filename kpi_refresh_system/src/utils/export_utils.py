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
    
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        for company_name, df in data_dict.items():
            # Excel sheet names have a 31 character limit and certain characters are not allowed
            sheet_name = company_name[:31]
            # Replace invalid characters
            for char in ['/', '\\', '?', '*', '[', ']', ':']:
                sheet_name = sheet_name.replace(char, '_')
            
            # Write DataFrame to sheet
            df.to_excel(writer, sheet_name=sheet_name, index=True)
            
            # Auto-adjust column widths
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                worksheet.set_column(idx + 1, idx + 1, min(max_len, 50))  # +1 because of index
    
    buffer.seek(0)
    return buffer.getvalue(), file_name