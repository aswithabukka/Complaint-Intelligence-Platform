import pandas as pd
from app.document_processors.base import BaseDocumentProcessor, ExtractionResult
from app.db.models.document import DocumentType


class ExcelProcessor(BaseDocumentProcessor):
    """Processor for Excel spreadsheets (.xls, .xlsx)."""

    SUPPORTED_TYPES = {DocumentType.XLS, DocumentType.XLSX, "xls", "xlsx"}

    def supports_file_type(self, file_type: str) -> bool:
        return file_type in self.SUPPORTED_TYPES

    def extract_text(self, file_path: str) -> ExtractionResult:
        # Read all sheets
        excel_file = pd.ExcelFile(file_path)
        text_parts = []
        sheet_info = []

        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)

            if df.empty:
                continue

            # Convert DataFrame to readable text
            sheet_text = self._dataframe_to_text(df, sheet_name)
            text_parts.append(sheet_text)

            sheet_info.append({
                "name": sheet_name,
                "rows": len(df),
                "columns": len(df.columns)
            })

        full_text = '\n\n'.join(text_parts)
        cleaned_text = self.postprocess(full_text)

        return ExtractionResult(
            text=cleaned_text,
            page_count=len(excel_file.sheet_names),
            metadata={
                "extraction_method": "pandas",
                "sheets": sheet_info
            }
        )

    def _dataframe_to_text(self, df: pd.DataFrame, sheet_name: str) -> str:
        """Convert a DataFrame to readable text format."""
        lines = [f"=== Sheet: {sheet_name} ===\n"]

        # Add column headers
        headers = ' | '.join(str(col) for col in df.columns)
        lines.append(f"Columns: {headers}\n")
        lines.append("-" * 50)

        # Add rows (limit to prevent huge output)
        max_rows = 100
        for idx, row in df.head(max_rows).iterrows():
            row_text = ' | '.join(str(val) for val in row.values)
            lines.append(row_text)

        if len(df) > max_rows:
            lines.append(f"\n... and {len(df) - max_rows} more rows")

        return '\n'.join(lines)
