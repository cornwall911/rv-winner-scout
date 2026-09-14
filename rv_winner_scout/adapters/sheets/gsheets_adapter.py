"""Google Sheets transactional updater with pre-mutation backups and date separators."""

import base64
import json
import logging
import os
from typing import Any, Dict, List, Optional
import gspread
from google.oauth2.service_account import Credentials

from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.exceptions import GoogleSheetsError
from rv_winner_scout.domain.models import ProductCandidate
from rv_winner_scout.ports.sheet_port import GoogleSheetsPort
from rv_winner_scout.services.backup_service import BackupService

logger = logging.getLogger(__name__)

SHEET_HEADERS = [
    "Research Date",
    "Product Name",
    "ASIN",
    "Amazon URL",
    "Amazon Price",
    "Walmart Status",
    "Walmart URL",
    "Walmart Price",
    "Walmart Match Type",
    "Walmart Search Keywords",
    "Product Newness Status",
    "Newness Evidence",
    "RV Pain Point",
    "Novelty / Discovery /10",
    "Visual WOW /10",
    "RV Facebook Exposure",
    "RV Audience Breadth",
    "Overall Score /100",
    "Traffic Potential vs 25K",
    "Confidence",
    "Visual Hook",
    "FB Post Angle",
    "Why This Could Be The Next Winner",
    "Why It Could Fail",
    "Exposure Sources",
    "Verification Status",
    "Not-Verified Notes",
    "Exception Label",
    "Run ID",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class GoogleSheetsAdapter(GoogleSheetsPort):
    """Synchronizes candidate winners transactionally to a single worksheet."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        backup_service: Optional[BackupService] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.backup_service = backup_service or BackupService(settings=self.settings)

    def _get_client(self) -> gspread.Client:
        """Initializes gspread authenticated client using service account credentials."""
        creds_val = self.settings.google_sheets_credentials_json
        if not creds_val:
            raise GoogleSheetsError("GOOGLE_SHEETS_CREDENTIALS_JSON is not configured.")

        creds_dict: Optional[Dict[str, Any]] = None

        # 1. Check if direct file path
        if os.path.exists(creds_val):
            try:
                with open(creds_val, "r", encoding="utf-8") as f:
                    creds_dict = json.load(f)
            except Exception as e:
                raise GoogleSheetsError(f"Failed to read credentials file: {e}") from e

        # 2. Check if raw JSON string
        elif creds_val.strip().startswith("{"):
            try:
                creds_dict = json.loads(creds_val)
            except Exception as e:
                raise GoogleSheetsError(f"Failed to parse credentials JSON string: {e}") from e

        # 3. Check if base64 encoded
        else:
            try:
                decoded = base64.b64decode(creds_val).decode("utf-8")
                creds_dict = json.loads(decoded)
            except Exception as e:
                raise GoogleSheetsError(f"Failed to decode base64 credentials: {e}") from e

        if not creds_dict:
            raise GoogleSheetsError("Could not resolve Google Service Account credentials.")

        credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(credentials)

    async def create_backup(self) -> str:
        """Snapshots the existing sheet rows locally if possible."""
        try:
            client = self._get_client()
            if not self.settings.spreadsheet_id:
                return "Spreadsheet ID not configured"
            sheet = client.open_by_key(self.settings.spreadsheet_id)
            worksheet = sheet.worksheet(self.settings.sheet_name)
            all_values = worksheet.get_all_values()
            return self.backup_service.backup_records("gsheet_snapshot", all_values)
        except Exception as e:
            logger.warning("Could not create remote sheet snapshot: %s", e)
            return "Remote snapshot skipped"

    async def append_winners(
        self,
        run_date: str,
        winners: List[ProductCandidate],
        run_id: str = "",
        reviewed_count: int = 0,
    ) -> int:
        """Appends date separator and product rows (or No Winner verdict) to worksheet."""
        if not self.settings.spreadsheet_id:
            raise GoogleSheetsError("SPREADSHEET_ID is not configured.")

        # Backup candidate payloads locally first
        if winners:
            self.backup_service.backup_records(f"winners_{run_date}", winners)

        client = self._get_client()
        sheet = client.open_by_key(self.settings.spreadsheet_id)

        try:
            worksheet = sheet.worksheet(self.settings.sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(
                title=self.settings.sheet_name, rows=1000, cols=len(SHEET_HEADERS)
            )

        existing_rows = worksheet.get_all_values()
        rows_to_insert: List[List[Any]] = []

        # If sheet is empty, insert header row
        if not existing_rows:
            rows_to_insert.append(SHEET_HEADERS)

        # Full-width horizontal date separator row
        separator_label = f"════════════════ {run_date} ════════════════"
        rows_to_insert.append([separator_label] + [""] * (len(SHEET_HEADERS) - 1))

        if not winners:
            # Add daily audit verdict row
            verdict_text = (
                f"I reviewed {reviewed_count} products from the link. None met the hidden-winner criteria today."
            )
            rows_to_insert.append([verdict_text] + [""] * (len(SHEET_HEADERS) - 1))
        else:
            for w in winners:
                title = w.verified_product.title if w.verified_product else w.raw_product.title
                price = w.verified_product.displayed_price if w.verified_product else w.raw_product.displayed_price
                price_str = f"${price:.2f}" if price is not None else "NOT VERIFIED"

                walmart_status = w.walmart.status.value if w.walmart else "NOT VERIFIED"
                walmart_url = w.walmart.url if w.walmart and w.walmart.url else "NOT FOUND"
                walmart_price_str = (
                    f"${w.walmart.displayed_price:.2f}"
                    if w.walmart and w.walmart.displayed_price is not None
                    else "NOT VERIFIED"
                )
                match_type = (
                    "Direct Alternative"
                    if w.walmart and w.walmart.is_direct_alternative
                    else "None"
                )
                walmart_keywords = w.walmart.search_query_used if w.walmart else ""

                novelty_str = (
                    f"{(w.scores.novelty_newness / 1.5):.1f}"
                    if w.scores
                    else ""
                )
                visual_str = (
                    f"{(w.scores.visual_wow / 1.0):.1f}"
                    if w.scores
                    else ""
                )
                score_str = (
                    f"{w.scores.total_score:.1f}"
                    if w.scores
                    else "0.0"
                )

                traffic_str = w.opportunity.traffic_benchmark.value if w.opportunity else ""
                confidence_str = w.opportunity.confidence.value if w.opportunity else ""
                visual_hook = w.opportunity.visual_hook if w.opportunity else ""
                fb_angle = w.opportunity.facebook_angle if w.opportunity else ""
                why_next = w.opportunity.why_next_winner if w.opportunity else ""
                why_fail = w.opportunity.why_fail if w.opportunity else ""
                exposure_sources = ", ".join([s.source_url for s in w.exposure_signals])
                verification_notes = (
                    w.verified_product.failure_reason
                    if w.verified_product and w.verified_product.failure_reason
                    else ""
                )
                exception_label = (
                    w.scores.exception_reason
                    if w.scores and w.scores.is_exception
                    else ""
                )

                row = [
                    run_date,
                    title,
                    w.asin,
                    w.canonical_url,
                    price_str,
                    walmart_status,
                    walmart_url,
                    walmart_price_str,
                    match_type,
                    walmart_keywords,
                    w.newness.value,
                    "; ".join(w.newness_evidence),
                    ", ".join(w.identified_pain_points),
                    novelty_str,
                    visual_str,
                    w.exposure_level.value,
                    w.audience_breadth.value,
                    score_str,
                    traffic_str,
                    confidence_str,
                    visual_hook,
                    fb_angle,
                    why_next,
                    why_fail,
                    exposure_sources,
                    w.verification_state.value,
                    verification_notes,
                    exception_label,
                    run_id,
                ]
                rows_to_insert.append(row)

        worksheet.append_rows(rows_to_insert, value_input_option="USER_ENTERED")
        return len(winners)
