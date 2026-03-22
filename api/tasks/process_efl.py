import asyncio
import logging

from database.connection import update_job_extracted_data, update_job_status
from models.efl import PDFType
from services.downloader import download_pdf
from services.efl_extractor import ExtractionError, extract_efl_data
from services.pdf_processor import extract_text

logger = logging.getLogger(__name__)


async def process_efl_task(job_id: str, efl_url: str):
    try:
        # Stage 1: Download PDF
        await update_job_status(job_id, "downloading")
        result = await download_pdf(efl_url)
        if not result.success:
            await update_job_status(job_id, "failed", error=result.error)
            return

        # Stage 2: Extract text and classify
        await update_job_status(job_id, "extracting")
        extraction = await asyncio.to_thread(extract_text, result.file_path)
        await update_job_status(
            job_id, "extracting", pdf_type=extraction.pdf_type.value
        )

        if extraction.pdf_type == PDFType.scanned:
            await update_job_status(
                job_id,
                "failed",
                error="PDF is scanned/image-based, cannot extract text",
            )
            return

        # Stage 3: Parse with LLM
        await update_job_status(job_id, "parsing")
        try:
            efl_data = await extract_efl_data(extraction.text)
        except ExtractionError as e:
            await update_job_status(
                job_id, "failed", error=f"LLM extraction failed: {e}"
            )
            return

        # Stage 4: Store results
        await update_job_status(job_id, "storing")
        await update_job_extracted_data(job_id, efl_data.model_dump_json())

    except Exception as e:
        logger.exception("EFL processing failed for job %s", job_id)
        await update_job_status(job_id, "failed", error=str(e))
