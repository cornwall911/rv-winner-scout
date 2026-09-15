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

    async def notify_run_started(
        self, mode: str, max_products: int
    ) -> dict[str, int]:
        """Sends an initial execution status message and returns {chat_id: message_id} for live in-place edits."""
        if not self.is_configured:
            return {}

        mode_label = "فحص شامل (Full Crawl)" if mode == "full" else f"فحص سريع ({mode})"
        text = (
            "🚀 <b>RV Winner Scout | بدء جولة الفحص اليومية</b>\n"
            "═══════════════════════════\n"
            f"⚙️ <b>الوضع:</b> <code>{mode_label}</code>\n"
            f"🎯 <b>السعة المتاحة:</b> حتى <code>{max_products:,}</code> منتج\n"
            "⏳ <b>الحالة:</b> جاري استكشاف التصنيفات وتفريعات RV New Releases...\n"
            "───────────────────────────\n"
            "🔄 <i>سيتم تحديث هذه الرسالة تلقائياً لبيان نسبة الإنجاز والوقت المتبقي...</i>"
        )

        message_map: dict[str, int] = {}
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        async with httpx.AsyncClient(timeout=15.0) as client:
            for cid in self.chat_ids:
                try:
                    res = await client.post(
                        url,
                        json={
                            "chat_id": cid,
                            "text": text,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True,
                        },
                    )
                    if res.status_code == 200:
                        data = res.json()
                        mid = data.get("result", {}).get("message_id")
                        if mid:
                            message_map[cid] = mid
                except Exception as exc:
                    logger.debug("Could not send run-start message to %s: %s", cid, exc)

        return message_map

    async def update_progress(
        self,
        message_map: dict[str, int],
        stage_name: str,
        current: int,
        total: int,
        elapsed_seconds: float,
    ) -> None:
        """Edits the active status message in Telegram with real-time progress bar, percentage, and ETA."""
        if not self.is_configured or not message_map:
            return

        pct = int(min(100, max(1, (current / total) * 100))) if total > 0 else 0
        filled = min(10, max(0, pct // 10))
        bar = "▓" * filled + "░" * (10 - filled)

        elapsed_mins = int(elapsed_seconds // 60)
        elapsed_str = f"{elapsed_mins} دقيقة" if elapsed_mins > 0 else f"{int(elapsed_seconds)} ثانية"

        if current > 0 and total > current:
            eta_secs = (elapsed_seconds / current) * (total - current)
            eta_mins = max(1, int(round(eta_secs / 60.0)))
            eta_str = f"~{eta_mins} دقيقة"
        elif current >= total and total > 0:
            eta_str = "وشك الانتهاء ⚡"
        else:
            eta_str = "جاري الحساب..."

        logger.info(
            "[PROGRESS] %d%% (%d/%d) | Stage: %s | Elapsed: %ds | ETA: %s",
            pct, current, total, stage_name, int(elapsed_seconds), eta_str
        )

        text = (
            "⏳ <b>RV Winner Scout | جاري الفحص الآن...</b>\n"
            "═══════════════════════════\n"
            f"📊 <b>مستوى التقدم:</b> <code>[{bar}] {pct}%</code>\n\n"
            f"📌 <b>المرحلة الحالية:</b> {stage_name}\n"
            f"🔢 <b>المنجز:</b> <code>{current} / {total}</code> منتج\n"
            f"⏱️ <b>الوقت المنقضي:</b> {elapsed_str}\n"
            f"⏳ <b>الوقت المتبقي تقريباً:</b> <b>{eta_str}</b>\n"
            "───────────────────────────\n"
            "🔄 <i>تتحدث هذه الرسالة تلقائياً لبيان حالة الفحص المباشر...</i>"
        )

        edit_url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
        async with httpx.AsyncClient(timeout=10.0) as client:
            for cid, mid in message_map.items():
                try:
                    await client.post(
                        edit_url,
                        json={
                            "chat_id": cid,
                            "message_id": mid,
                            "text": text,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True,
                        },
                    )
                except Exception as exc:
                    logger.debug("Failed to edit progress message for %s: %s", cid, exc)

    async def finish_progress_message(self, message_map: dict[str, int]) -> None:
        """Updates the progress message to indicate full completion."""
        if not self.is_configured or not message_map:
            return

        text = (
            "✅ <b>RV Winner Scout | اكتمل الفحص اليومي بنجاح!</b>\n"
            "═══════════════════════════\n"
            "📊 تم الانتهاء من كافة مراحل التحقق وتقييم الذكاء الاصطناعي.\n"
            "👇 <b>التفاصيل والمنتجات الفائزة ورابط الداشبورد في التقرير أدناه:</b>"
        )

        edit_url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
        async with httpx.AsyncClient(timeout=10.0) as client:
            for cid, mid in message_map.items():
                try:
                    await client.post(
                        edit_url,
                        json={
                            "chat_id": cid,
                            "message_id": mid,
                            "text": text,
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True,
                        },
                    )
                except Exception as exc:
                    logger.debug("Failed to finish progress message for %s: %s", cid, exc)

    async def notify_run_completed(
        self,
        reviewed_count: int,
        winners: List[ProductCandidate],
        near_misses: List[ProductCandidate],
        health: RunHealthReport,
        should_be_tested: Optional[List[ProductCandidate]] = None,
    ) -> bool:
        """Sends daily run verdict with winner highlights or near-miss summary."""
        if not self.is_configured:
            return False

        sheet_link = (
            f"https://docs.google.com/spreadsheets/d/{self.settings.spreadsheet_id}/edit"
            if self.settings.spreadsheet_id
            else "https://docs.google.com"
        )
        dashboard_url = "https://almostafa-scout.workers.dev/"

        date_str = health.end_time.strftime("%Y-%m-%d")

        change_line = ""
        if health.products_changed > 0:
            change_line = (
                f"🔄 <b>تغييرات المنتجات:</b> رصد تحديثات في <b>{health.products_changed}</b> منتج "
                f"(📈 تحسن: <b>{health.products_improved}</b> | 📉 تراجع: <b>{health.products_declined}</b>)"
            )
        elif health.duplicates_prevented > 0:
            change_line = f"🔄 <b>تحديثات المنتجات:</b> تم منع تكرار {health.duplicates_prevented} منتج متطابق دون تغيير"

        if winners:
            lines = [
                "🏆 <b>RV Winner Scout | اكتشاف فائزين جدد!</b>",
                "═══════════════════════════",
                f"📅 <b>التاريخ:</b> <code>{date_str}</code>",
                f"🔍 <b>إجمالي المنتجات المفحوصة:</b> {reviewed_count}",
                f"✨ <b>عدد المنتجات الفائزة (+80):</b> {len(winners)}",
            ]
            if change_line:
                lines.append(change_line)
            lines.extend([
                "",
                "⭐ <b>تفاصيل المنتجات الفائزة:</b>",
                "───────────────────────────",
            ])
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
                f"🌐 <a href='{dashboard_url}'>عرض الداشبورد التفاعلي المباشر (Live Dashboard)</a>",
            ])
            msg = "\n".join(lines)
        elif should_be_tested:
            lines = [
                "🧪 <b>RV Winner Scout | منتجات مرشحة للاختبار (Should Be Tested)!</b>",
                "═══════════════════════════",
                f"📅 <b>التاريخ:</b> <code>{date_str}</code>",
                f"🔍 <b>إجمالي المفحوص اليوم:</b> {reviewed_count}",
                f"🧪 <b>منتجات ذات أولوية للاختبار:</b> {len(should_be_tested)}",
            ]
            if change_line:
                lines.append(change_line)
            lines.extend([
                "",
                "⚡ <b>أبرز المنتجات عالية الفائدة وحل المشكلات:</b>",
                "───────────────────────────",
            ])
            for i, st in enumerate(should_be_tested[:3], 1):
                raw_title = st.verified_product.title if st.verified_product else st.raw_product.title
                title = html.escape(raw_title[:65] + ("..." if len(raw_title) > 65 else ""))
                score = st.scores.total_score if st.scores else 0.0
                price = f"${st.verified_product.displayed_price:.2f}" if st.verified_product and st.verified_product.displayed_price else "N/A"
                hook = html.escape(st.opportunity.visual_hook) if st.opportunity else "High Utility Problem Solver"

                lines.extend([
                    f"🧪 <b>{i}. {title}</b>",
                    f"   • <b>التقييم:</b> <code>{score:.1f} / 100</code>",
                    f"   • <b>سعر أمازون:</b> {price}",
                    f"   • <b>الميزة / الخطاف:</b> <i>{hook}</i>",
                    f"   • 🔗 <a href='{st.canonical_url}'>معاينة المنتج على أمازون</a>",
                    "",
                ])

            lines.extend([
                "═══════════════════════════",
                f"👉 <a href='{sheet_link}'>فتح سجل Research Log في Google Sheets</a>",
                f"🌐 <a href='{dashboard_url}'>عرض الداشبورد التفاعلي المباشر (Live Dashboard)</a>",
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
            if change_line:
                lines.append(change_line)
            lines.extend(top_near_miss_lines)
            lines.extend([
                "",
                "═══════════════════════════",
                f"👉 <a href='{sheet_link}'>فتح سجل Research Log في Google Sheets</a>",
                f"🌐 <a href='{dashboard_url}'>عرض الداشبورد التفاعلي المباشر (Live Dashboard)</a>",
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
