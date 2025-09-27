import pandas as pd
import numpy as np
from typing import List, Dict, Any
import os
from pathlib import Path
import asyncio
from bs4 import BeautifulSoup
import PyPDF2
import json
import re
from .models import GroundWaterData, TextChunk
from .database import db_manager
from .vector_store import vector_store
import logging

logger = logging.getLogger(__name__)


class DataPreprocessor:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.structured_dir = self.data_dir / "structure_tables"

    async def process_all_data(self):
        """Process all data and populate databases"""
        logger.info("Starting data preprocessing...")

        # Process structured data
        groundwater_data = await self.process_structured_data()
        if groundwater_data:
            await db_manager.store_groundwater_data(groundwater_data)

        # Process unstructured data
        text_chunks = await self.process_unstructured_data()
        if text_chunks:
            await db_manager.store_text_chunks(text_chunks)
            vector_store.add_documents(text_chunks)
            vector_store.save_index()

        logger.info("Data preprocessing completed")

    async def process_structured_data(self) -> List[GroundWaterData]:
        """Process CSV and Excel files containing structured data"""
        logger.info("Processing structured data...")
        groundwater_data = []

        # Process CSV files
        csv_files = list(self.structured_dir.glob("*.csv"))
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                data = self._process_groundwater_csv(df, str(csv_file))
                groundwater_data.extend(data)
                logger.info(f"Processed {len(data)} records from {csv_file.name}")
            except Exception as e:
                logger.error(f"Error processing {csv_file}: {e}")

        # Process Excel files
        excel_files = list(self.structured_dir.glob("*.xlsx"))
        for excel_file in excel_files:
            try:
                # Read all sheets
                excel_data = pd.read_excel(excel_file, sheet_name=None)
                for sheet_name, df in excel_data.items():
                    data = self._process_excel_sheet(df, str(excel_file), sheet_name)
                    groundwater_data.extend(data)
                    logger.info(
                        f"Processed {len(data)} records from {excel_file.name} - {sheet_name}"
                    )
            except Exception as e:
                logger.error(f"Error processing {excel_file}: {e}")

        return groundwater_data

    def _process_groundwater_csv(
        self, df: pd.DataFrame, source: str
    ) -> List[GroundWaterData]:
        """Process groundwater data from CSV"""
        data = []

        # Clean column names
        df.columns = df.columns.str.strip()

        # Expected columns for groundwater data
        required_columns = [
            "STATE",
            "Rainfall (mm)",
            "Ground Water Extraction (ham)",
            "Annual Extractable Ground Water Resources (ham)",
        ]

        if all(col in df.columns for col in required_columns):
            for _, row in df.iterrows():
                try:
                    # Clean numeric values (remove commas)
                    rainfall = self._clean_numeric(row["Rainfall (mm)"])
                    extraction = self._clean_numeric(
                        row["Ground Water Extraction (ham)"]
                    )
                    resources = self._clean_numeric(
                        row["Annual Extractable Ground Water Resources (ham)"]
                    )

                    groundwater_record = GroundWaterData(
                        state=str(row["STATE"]).strip(),
                        rainfall_mm=rainfall,
                        ground_water_extraction_ham=extraction,
                        annual_extractable_ground_water_resources_ham=resources,
                        url=row.get("web-scraper-start-url", ""),
                        year="2024-2025",
                    )
                    data.append(groundwater_record)
                except Exception as e:
                    logger.warning(f"Error processing row: {e}")
                    continue

        return data

    def _process_excel_sheet(
        self, df: pd.DataFrame, source: str, sheet_name: str
    ) -> List[GroundWaterData]:
        """Process Excel sheet data"""
        # Similar logic to CSV processing but adapted for Excel format
        data = []

        # Try to identify data structure
        if df.empty:
            return data

        # Look for state/location information
        for _, row in df.iterrows():
            try:
                # Extract meaningful data from each row
                # This is a generic processor - adjust based on actual Excel structure
                row_dict = row.to_dict()

                # Create text chunk for unstructured data from Excel
                content = f"Sheet: {sheet_name}\n"
                for key, value in row_dict.items():
                    if pd.notna(value):
                        content += f"{key}: {value}\n"

                # Create text chunk for vector search
                text_chunk = TextChunk(
                    content=content,
                    source=source,
                    source_type="xlsx",
                    metadata={
                        "sheet_name": sheet_name,
                        "row_data": {
                            k: str(v) for k, v in row_dict.items() if pd.notna(v)
                        },
                    },
                )

                # Store as text chunk instead of structured data for Excel files
                # unless we can identify specific groundwater data structure

            except Exception as e:
                logger.warning(f"Error processing Excel row: {e}")
                continue

        return data

    async def process_unstructured_data(self) -> List[TextChunk]:
        """Process PDFs, HTML, and other unstructured data"""
        logger.info("Processing unstructured data...")
        text_chunks = []

        # Process HTML files
        html_files = list(self.raw_dir.rglob("*.html"))
        for html_file in html_files:
            chunks = self._process_html_file(html_file)
            text_chunks.extend(chunks)
            logger.info(f"Processed {len(chunks)} chunks from {html_file.name}")

        # Process PDF files
        pdf_files = list(self.raw_dir.rglob("*.pdf"))
        for pdf_file in pdf_files:
            chunks = self._process_pdf_file(pdf_file)
            text_chunks.extend(chunks)
            logger.info(f"Processed {len(chunks)} chunks from {pdf_file.name}")

        return text_chunks

    def _process_html_file(self, file_path: Path) -> List[TextChunk]:
        """Extract and chunk text from HTML files"""
        chunks = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            # Extract FAQ items (based on the structure seen)
            faq_items = soup.find_all("div", class_="card")

            for i, faq_item in enumerate(faq_items):
                question_elem = faq_item.find("button")
                answer_elem = faq_item.find("div", class_="card-body")

                if question_elem and answer_elem:
                    question = question_elem.get_text(strip=True)
                    answer = answer_elem.get_text(strip=True)

                    content = f"Q: {question}\nA: {answer}"

                    chunk = TextChunk(
                        content=content,
                        source=str(file_path),
                        source_type="html",
                        metadata={
                            "question": question,
                            "answer": answer,
                            "faq_index": i,
                            "source_file": file_path.name,
                        },
                    )
                    chunks.append(chunk)

        except Exception as e:
            logger.error(f"Error processing HTML file {file_path}: {e}")

        return chunks

    def _process_pdf_file(self, file_path: Path) -> List[TextChunk]:
        """Extract and chunk text from PDF files"""
        chunks = []
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)

                full_text = ""
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    full_text += text + "\n"

                # Split into chunks (approximately 1000 characters each)
                chunk_size = 1000
                overlap = 200

                for i in range(0, len(full_text), chunk_size - overlap):
                    chunk_text = full_text[i : i + chunk_size]

                    if len(chunk_text.strip()) > 50:  # Only include substantial chunks
                        chunk = TextChunk(
                            content=chunk_text.strip(),
                            source=str(file_path),
                            source_type="pdf",
                            metadata={
                                "chunk_index": i // (chunk_size - overlap),
                                "source_file": file_path.name,
                                "total_pages": len(reader.pages),
                            },
                        )
                        chunks.append(chunk)

        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {e}")

        return chunks

    def _clean_numeric(self, value: str) -> float:
        """Clean and convert numeric strings to float"""
        if pd.isna(value):
            return 0.0

        # Convert to string and remove commas
        clean_value = str(value).replace(",", "").strip()

        try:
            return float(clean_value)
        except (ValueError, TypeError):
            return 0.0

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about processed data"""
        stats = {
            "structured_files": {
                "csv_files": len(list(self.structured_dir.glob("*.csv"))),
                "excel_files": len(list(self.structured_dir.glob("*.xlsx"))),
            },
            "unstructured_files": {
                "html_files": len(list(self.raw_dir.rglob("*.html"))),
                "pdf_files": len(list(self.raw_dir.rglob("*.pdf"))),
            },
        }
        return stats


# Global preprocessor instance
preprocessor = DataPreprocessor()
