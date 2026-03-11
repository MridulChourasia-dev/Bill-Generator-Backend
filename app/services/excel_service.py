import pandas as pd
from pathlib import Path
import uuid
from typing import List, Dict, Any
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ExcelService:
    """Service for generating Excel reports and bill exports."""

    def __init__(self):
        self.output_dir = Path(settings.UPLOAD_DIR) / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_bill_export(self, bills: List[Dict[str, Any]], filename_prefix: str = "bills_export") -> Path:
        """
        Exports a list of bills to an Excel file.
        Expects a list of dictionaries with bill details.
        """
        try:
            df = pd.DataFrame(bills)
            
            # Reorder or select specific columns if needed
            # For example:
            # df = df[['title', 'amount', 'vendor', 'category', 'status', 'due_date', 'bill_date']]
            
            file_name = f"{filename_prefix}_{uuid.uuid4().hex[:8]}.xlsx"
            file_path = self.output_dir / file_name
            
            # Use openpyxl as the engine
            df.to_excel(file_path, index=False, engine='openpyxl')
            
            logger.info(f"Generated Excel export: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to generate Excel export: {str(e)}")
            raise

excel_service = ExcelService()
