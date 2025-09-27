import pandas as pd
from typing import List, Dict, Any
from pathlib import Path
import asyncio
import logging
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader, BSHTMLLoader, CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .models import GroundWaterData
from .database import db_manager
from .vector_store import vector_store

logger = logging.getLogger(__name__)


class DataPreprocessor:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to data directory relative to this file's location
            base_dir = Path(__file__).parent.parent
            self.data_dir = base_dir / "data"
        else:
            self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.structured_dir = self.data_dir / "structure_tables"
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    async def process_all_data(self):
        """Process all data and populate databases"""
        logger.info("Starting data preprocessing...")

        # Process structured data
        groundwater_data = await self.process_structured_data()
        if groundwater_data:
            await db_manager.store_groundwater_data(groundwater_data)
            
            # Also create documents for vector store from structured data
            structured_documents = self._create_documents_from_structured_data(groundwater_data)
            vector_store.add_documents(structured_documents)
            logger.info(f"Added {len(structured_documents)} structured data documents to vector store")

        # Process unstructured data
        documents = await self.process_unstructured_data()
        if documents:
            vector_store.add_documents(documents)
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
                df = pd.read_excel(excel_file)
                data = self._process_groundwater_excel(df, str(excel_file))
                groundwater_data.extend(data)
                logger.info(f"Processed {len(data)} records from {excel_file.name}")
            except Exception as e:
                logger.error(f"Error processing {excel_file}: {e}")

        return groundwater_data

    def _process_groundwater_excel(self, df: pd.DataFrame, source: str) -> List[GroundWaterData]:
        """Process groundwater data from Excel"""
        data = []
        
        # Find header row (usually contains "S.No" and "STATE")
        header_row_index = -1
        for i, row in df.iterrows():
            row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
            if "S.No" in row_str and "STATE" in row_str:
                header_row_index = i
                break

        if header_row_index == -1:
            logger.warning(f"Could not find header row in {source}")
            return data

        # Start processing data from the row after headers (skip potential sub-headers)
        data_start_row = header_row_index + 3
        
        # Extract data
        for i in range(data_start_row, len(df)):
            try:
                row = df.iloc[i]
                
                # Get state name from column 1 (usually the STATE column)
                state = row.iloc[1] if len(row) > 1 else None
                if pd.isna(state) or str(state).strip() == "":
                    continue
                
                state_str = str(state).strip().upper()
                
                # Skip total/summary rows
                if any(keyword in state_str.lower() for keyword in ['total', 'grand', 'sum', 'all']):
                    continue
                
                # Extract rainfall (usually around column 5-6)
                rainfall = 0.0
                for col_idx in [5, 6, 7]:
                    if col_idx < len(row) and pd.notna(row.iloc[col_idx]):
                        rainfall = self._clean_numeric(row.iloc[col_idx])
                        if rainfall > 0:
                            break
                
                # For extraction and resources, we need to look at the right columns
                # Based on our analysis, extraction might be around column 66, resources around 90
                # But let's also look for the "Total Ground Water Availability" which was in column 151
                extraction = 0.0
                resources = 0.0
                
                # Look for ground water availability (this was in column 151 for Delhi)
                if len(row) > 151 and pd.notna(row.iloc[151]):
                    resources = self._clean_numeric(row.iloc[151])
                
                # If we don't have resources from column 151, try other columns
                if resources == 0:
                    for col_idx in [90, 91, 92]:
                        if col_idx < len(row) and pd.notna(row.iloc[col_idx]):
                            resources = self._clean_numeric(row.iloc[col_idx])
                            if resources > 0:
                                break
                
                # For extraction, try multiple columns
                for col_idx in [66, 67, 68]:
                    if col_idx < len(row) and pd.notna(row.iloc[col_idx]):
                        extraction = self._clean_numeric(row.iloc[col_idx])
                        if extraction > 0:
                            break
                
                # If we have valid data, create a record
                if rainfall > 0 or extraction > 0 or resources > 0:
                    groundwater_record = GroundWaterData(
                        state=state_str,
                        rainfall_mm=rainfall,
                        ground_water_extraction_ham=extraction,
                        annual_extractable_ground_water_resources_ham=resources,
                        url=source,
                        year="2023-2024",
                    )
                    data.append(groundwater_record)
                    
            except Exception as e:
                logger.warning(f"Error processing row {i} in {source}: {e}")
                continue
                
        logger.info(f"Extracted {len(data)} records from Excel file {source}")
        return data


    def _process_groundwater_csv(
        self, df: pd.DataFrame, source: str
    ) -> List[GroundWaterData]:
        """Process groundwater data from CSV"""
        data = []
        df.columns = df.columns.str.strip()
        required_columns = [
            "STATE",
            "Rainfall (mm)",
            "Ground Water Extraction (ham)",
            "Annual Extractable Ground Water Resources (ham)",
        ]

        if all(col in df.columns for col in required_columns):
            for _, row in df.iterrows():
                try:
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

    async def process_unstructured_data(self) -> List[Document]:
        """Process PDFs, HTML, and other unstructured data"""
        logger.info("Processing unstructured data...")
        documents = []

        # Process HTML files
        html_files = list(self.raw_dir.rglob("*.html"))
        for html_file in html_files:
            loader = BSHTMLLoader(str(html_file))
            docs = loader.load()
            documents.extend(self.text_splitter.split_documents(docs))
            logger.info(f"Processed {len(docs)} chunks from {html_file.name}")

        # Process PDF files
        pdf_files = list(self.raw_dir.rglob("*.pdf"))
        for pdf_file in pdf_files:
            loader = PyPDFLoader(str(pdf_file))
            docs = loader.load()
            documents.extend(self.text_splitter.split_documents(docs))
            logger.info(f"Processed {len(docs)} chunks from {pdf_file.name}")

        return documents

    def _clean_numeric(self, value: str) -> float:
        """Clean and convert numeric strings to float"""
        if pd.isna(value):
            return 0.0
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

    def _create_documents_from_structured_data(self, groundwater_data: List[GroundWaterData]) -> List[Document]:
        """Create documents from structured groundwater data for vector store"""
        documents = []
        
        for data in groundwater_data:
            # Create comprehensive content about each state's groundwater data
            content = f"""
State: {data.state}
Year: {data.year}

Groundwater Information for {data.state}:
- Annual Rainfall: {data.rainfall_mm} mm
- Ground Water Extraction: {data.ground_water_extraction_ham} ham (hectare-meters)
- Annual Extractable Ground Water Resources: {data.annual_extractable_ground_water_resources_ham} ham
- Ground Water Utilization: {(data.ground_water_extraction_ham / data.annual_extractable_ground_water_resources_ham * 100):.2f}%

The groundwater situation in {data.state} shows:
- Current extraction levels at {data.ground_water_extraction_ham} ham
- Total available resources of {data.annual_extractable_ground_water_resources_ham} ham  
- Rainfall contribution of {data.rainfall_mm} mm annually
- Utilization rate of {(data.ground_water_extraction_ham / data.annual_extractable_ground_water_resources_ham * 100):.2f}% of available resources

This data is from the INGRES (Integrated Groundwater Resource Information System) database for the year {data.year}.
            """.strip()
            
            # Create metadata
            metadata = {
                "state": data.state,
                "year": data.year,
                "type": "groundwater_data",
                "rainfall_mm": data.rainfall_mm,
                "extraction_ham": data.ground_water_extraction_ham,
                "resources_ham": data.annual_extractable_ground_water_resources_ham,
                "utilization_percent": round(data.ground_water_extraction_ham / data.annual_extractable_ground_water_resources_ham * 100, 2)
            }
            
            doc = Document(page_content=content, metadata=metadata)
            documents.append(doc)
            
        return documents


# Global preprocessor instance
preprocessor = DataPreprocessor()
