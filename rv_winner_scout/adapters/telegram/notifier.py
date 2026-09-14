"""Telegram notifications adapter for execution alerts and daily summaries."""

import html
import logging
from typing import List, Optional
import httpx

from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.models import ProductCandidate, RunHealthReport

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Dispatches clean, well-formatted alerts and daily summaries to Telegram."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.bot_token = self.settings.telegram_bot_token
        self.raw_chat_id = self.settings.telegram_chat_id

    @property
    def chat_ids(self) -> List[str]:
        if not self.raw_chat_id:
            return []
        return [cid.strip() for cid in self.raw_chat_id.split(",") if cid.strip()]

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_ids)

    async def send_message(self, text: str) -> bool:
        if not self.is_configured:
            return False

        success = False
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        async with httpx.AsyncClient(timeout=15.0) as client:
            for cid in self.chat_ids:
                payload = {
                    "chat_id": cid,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
                try:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        success = True
                    else:
                        logger.warning("Telegram notification failed for %s: %s", cid, res.text)
                except Exception as e:
                    logger.warning("Failed to send Telegram notification to %s: %s", cid, e)

        return success

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
            else "https://docs.google.com"
        )

        date_str = health.end_time.strftime("%Y-%m-%d")

        if winners:
            lines = [
                "🏆 <b>RV Winner Scout | اكتشاف فائزين جدد!</b>",
                "═══════════════════════════",
                f"📅 <b>التاريخ:</b> <code>{date_str}</code>",
                f"🔍 <b>إجمالي المنتجات المفحوصة:</b> {reviewed_count}",
                f"✨ <b>عدد المنتجات الفائزة (+80):</b> {len(winners)}",
                "",
                "⭐ <b>تفاصيل المنتجات الفائزة:</b>",
                "───────────────────────────",
            ]
            for i, w in enumerate(winners, 1):
                raw_title = w.verified_product.title if w.verified_product else w.raw_product.title
                title = html.escape(raw_title[:65] + ("..." if len(raw_title) > 65 else ""))
                score = w.scores.total_score if w.scores else 0.0
                price = f"${w.verified_product.displayed_price:.2f}" if w.verified_product and w.verified_product.displayed_price else "N/A"
                hook = html.escape(w.opportunity.visual_hook) if w.opportunity else "N/A"

                lines.extend([
                    f"🥇 <b>{i}. {title}</b>",
                    f"   • <b>التقييم:</b> <code>{score:.1f} / 100</code>",
                    f"   • <b>سعر أمازون:</b> {price}",
                    f"   • <b>الخطاف الإعلاني:</b> <i>{hook}</i>",
                    f"   • 🔗 <a href='{w.canonical_url}'>معاينة المنتج على أمازون</a>",
                    "",
                ])

            lines.extend([
                "═══════════════════════════",
                "📊 <b>تم تسجيل كافة التفاصيل في الشيت:</b>",
                f"👉 <a href='{sheet_link}'>فتح جدول Research Log في Google Sheets</a>",
                "🌐 <a href='https://cornwall911.github.io/rv-winner-scout/'>عرض الداشبورد التفاعلي المباشر (Live Dashboard)</a>",
            ])
            msg = "\n".join(lines)
        else:
            top_near_miss_lines = []
            if near_misses:
                nm = near_misses[0]
                nm_raw_title = nm.verified_product.title if nm.verified_product else nm.raw_product.title
                nm_title = html.escape(nm_raw_title[:65] + ("..." if len(nm_raw_title) > 65 else ""))
                nm_score = nm.scores.total_score if nm.scores else 0.0
                nm_link = nm.canonical_url
                reason = html.escape(nm.rejection_reason or "لم يتخطى حاجز 80 نقطة")

                top_near_miss_lines = [
                    "",
                    "👀 <b>أقرب منتج مرشح (Top Near Miss):</b>",
                    "───────────────────────────",
                    f"• <b>الاسم:</b> {nm_title}",
                    f"• <b>التقييم:</b> <code>{nm_score:.1f} / 100</code>",
                    f"• <b>السبب:</b> {reason}",
                    f"• 🔗 <a href='{nm_link}'>معاينة على أمازون</a>",
                ]

            lines = [
                "📊 <b>RV Winner Scout | التقرير اليومي</b>",
                "═══════════════════════════",
                f"📅 <b>التاريخ:</b> <code>{date_str}</code>",
                f"🔍 <b>المنتجات المفحوصة اليوم:</b> {reviewed_count}",
                "🎯 <b>النتيجة:</b> لا يوجد منتج حقق معيار الفوز اليوم (80+)",
                "📝 <b>حالة الشيت:</b> تم توثيق سطر الفحص اليومي بنجاح ✅",
            ]
            lines.extend(top_near_miss_lines)
            lines.extend([
                "",
                "═══════════════════════════",
                f"👉 <a href='{sheet_link}'>فتح سجل Research Log في Google Sheets</a>",
                "🌐 <a href='https://cornwall911.github.io/rv-winner-scout/'>عرض الداشبورد التفاعلي المباشر (Live Dashboard)</a>",
            ])
            msg = "\n".join(lines)

        if health.failed_sources or health.circuit_breakers_tripped or health.degraded_components:
            notes = ["\n⚠️ <i>ملاحظات تشغيلية:</i>"]
            if health.circuit_breakers_tripped:
                notes.append(f"• قواطع الدائرة: {', '.join(health.circuit_breakers_tripped)}")
            if health.degraded_components:
                notes.append(f"• المكونات المتأثرة: {', '.join(health.degraded_components)}")
            msg += "\n" + "\n".join(notes)

        return await self.send_message(msg)

    async def notify_failure(self, error_message: str, run_id: str = "") -> bool:
        """Sends immediate alert if the scraper crashes or is blocked."""
        if not self.is_configured:
            return False

        clean_error = html.escape(error_message)
        lines = [
            "🚨 <b>RV Winner Scout | تنبيه طارئ!</b>",
            "═══════════════════════════",
            "⚠️ <b>حدث خطأ أثناء عملية الفحص:</b>",
            f"<code>{clean_error}</code>",
            "",
            f"⏱️ <b>معرّف التشغيل (Run ID):</b> <code>{run_id}</code>",
            "═══════════════════════════",
            "يرجى مراجعة سجلات GitHub Actions أو التأكد من الكوتا / الكابتشا.",
        ]
        return await self.send_message("\n".join(lines))
