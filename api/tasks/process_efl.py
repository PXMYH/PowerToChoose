import asyncio
import logging

from database.connection import update_job_status
from models.efl import PDFType
from services.downloader import download_pdf
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

        # Stage 3: Parse with LLM (stub for Phase 2)
        await update_job_status(job_id, "parsing")
        # TODO: Phase 2 will add LLM parsing here

        # Stage 4: Store results (stub for Phase 3)
        await update_job_status(job_id, "storing")
        # TODO: Phase 3 will add database storage here

        # Complete
        await update_job_status(job_id, "completed")

    except Exception as e:
        logger.exception("EFL processing failed for job %s", job_id)
        await update_job_status(job_id, "failed", error=str(e))
