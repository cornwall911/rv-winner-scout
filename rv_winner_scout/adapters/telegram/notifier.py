"""Telegram notifications adapter for execution alerts and daily summaries."""

import logging
from typing import List, Optional
import httpx

from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Dispatches alerts and run conclusions to a specified Telegram chat."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.bot_token = self.settings.telegram_bot_token
        self.chat_id = self.settings.telegram_chat_id

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_message(self, text: str) -> bool:
        if not self.is_configured:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    logger.info("Telegram notification sent successfully.")
                    return True
                logger.warning("Telegram notification failed (status %s): %s", res.status_code, res.text)
                return False
        except Exception as e:
            logger.warning("Failed to send Telegram notification: %s", e)
            return False

    async def notify_run_completed(
        self,
        reviewed_count: int,
        winners: List[ProductCandidate],
        near_misses: List[ProductCandidate],
        health: RunHealthReport,
    ) -> bool:
        """Sends daily run verdict with winner highlights or near-miss summary."""
        if not self.is_configured:
            return False

        sheet_link = (
            f"https://docs.google.com/spreadsheets/d/{self.settings.spreadsheet_id}/edit#gid=1055207818"
            if self.settings.spreadsheet_id
            else "Google Sheets"
        )

        if winners:
            msg = (
                f"🚀 <b>RV Winner Scout — تم العثور على منتجات فائزة!</b>\n\n"
                f"✅ <b>تم فحص:</b> {reviewed_count} منتجاً\n"
                f"🏆 <b>عدد الفائزين (+80):</b> {len(winners)}\n"
                f"📊 <b>تم التحديث في الشيت:</b> بنجاح ✅\n\n"
                f"<b>المنتجات الفائزة:</b>\n"
            )
            for i, w in enumerate(winners, 1):
                title = w.verified_product.title if w.verified_product else w.raw_product.title
                score = w.scores.total_score if w.scores else 0.0
                price = f"${w.verified_product.displayed_price:.2f}" if w.verified_product and w.verified_product.displayed_price else "N/A"
                msg += f"{i}. <a href='{w.canonical_url}'>{title[:60]}...</a>\n   ⭐ Score: <b>{score:.1f}/100</b> | Price: {price}\n"

            msg += f"\n🔗 <a href='{sheet_link}'>عرض التفاصيل في Google Sheets</a>"
        else:
            top_near_miss = ""
            if near_misses:
                nm = near_misses[0]
                nm_title = nm.verified_product.title if nm.verified_product else nm.raw_product.title
                nm_score = nm.scores.total_score if nm.scores else 0.0
                top_near_miss = f"\n🔍 <b>أقرب منتج (Near Miss):</b>\n{nm_title[:60]}... (Score: {nm_score:.1f}/100)"

            msg = (
                f"ℹ️ <b>RV Winner Scout — تقرير الفحص اليومي</b>\n\n"
                f"تمت مراجعة <b>{reviewed_count}</b> منتجاً من Amazon New Releases اليوم.\n"
                f"❌ لم يتجاوز أي منتج معيار الـ Winner الصارم (+80).\n"
                f"📝 تم توثيق النتيجة وسطر الفحص اليومي في الشيت بنجاح.{top_near_miss}\n\n"
                f"🔗 <a href='{sheet_link}'>فتح سجل Research Log</a>"
            )

        # Check if there were degraded components or failed sources
        if health.failed_sources or health.circuit_breakers_tripped or health.degraded_components:
            msg += "\n\n⚠️ <i>ملاحظات تشغيلية:</i>"
            if health.circuit_breakers_tripped:
                msg += f"\n- Circuit Breakers: {', '.join(health.circuit_breakers_tripped)}"
            if health.degraded_components:
                msg += f"\n- Degraded: {', '.join(health.degraded_components)}"

        return await self.send_message(msg)

    async def notify_failure(self, error_message: str, run_id: str = "") -> bool:
        """Sends immediate alert if the scraper crashes or is blocked."""
        if not self.is_configured:
            return False

        msg = (
            f"🚨 <b>RV Winner Scout — تنبيه خطأ في الفحص!</b>\n\n"
            f"<b>تفاصيل المشكلة:</b>\n<code>{error_message}</code>\n\n"
            f"<b>Run ID:</b> {run_id}\n"
            f"يرجى مراجعة التقرير أو إعدادات السيرفر/الكابتشا/الكوتا."
        )
        return await self.send_message(msg)
