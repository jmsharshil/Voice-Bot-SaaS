import logging
import re
from datetime import datetime, date, time as dt_time, timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Sum
from django.utils import timezone

from conversations.models import (
    SarvamCampaign,
    SarvamCallRecord,
    SarvamAgent,
    DailyCampaignSummaryConfig
)

logger = logging.getLogger(__name__)
IST_TZ = ZoneInfo("Asia/Kolkata")


def generate_and_send_daily_summary(target_date: date = None, force: bool = False, custom_recipients: list = None, dummy: bool = False):
    """
    Generates and sends the comprehensive daily campaign summary email.
    
    Contains:
      1. Overall daily performance KPIs (campaigns run, total leads, answered rate, billed minutes).
      2. Breakdown of every campaign run today (Name, Agent, User who triggered, Total leads, Answered, Missed, Status).
      3. Live quota status for every Voice Agent (Allocated mins, Used today, Remaining minutes, Quota status).
    
    Args:
        target_date: Date to summarize (defaults to today in IST).
        force: If True, sends even if disabled in config or already sent today.
        custom_recipients: Optional list of emails to override the configured recipients (useful for test sends).
    """
    config = DailyCampaignSummaryConfig.get_config()

    if not config.is_enabled and not force:
        logger.info("ℹ️ [DAILY SUMMARY EMAIL]: Automated summary is disabled in config. Skipping.")
        return {"status": "skipped", "message": "Daily summary email is currently disabled."}

    # Determine recipients
    recipients = custom_recipients if custom_recipients else config.get_clean_email_list()
    if not recipients:
        logger.warning("⚠️ [DAILY SUMMARY EMAIL]: No valid recipient email addresses configured.")
        return {"status": "error", "message": "No valid recipient email addresses configured."}

    # Determine target date in IST
    now_ist = timezone.localtime(timezone.now(), IST_TZ)
    if not target_date:
        target_date = now_ist.date()

    # Check if already sent today (unless forced)
    if not force and config.last_sent_date == target_date:
        logger.info(f"ℹ️ [DAILY SUMMARY EMAIL]: Already sent for date {target_date}. Skipping duplicate send.")
        return {"status": "skipped", "message": f"Summary email already sent for {target_date}."}

    # Date range for target date in IST
    t_min = timezone.make_aware(datetime.combine(target_date, dt_time.min), IST_TZ)
    t_max = timezone.make_aware(datetime.combine(target_date, dt_time.max), IST_TZ)
    date_display_str = target_date.strftime("%d %b %Y")

    # 1. Fetch Today's Campaigns (or populate dummy if requested for testing)
    campaigns_list = []
    total_campaign_leads = 0
    total_campaign_answered = 0
    total_campaign_missed = 0

    if dummy:
        campaigns_list = [
            {
                "index": 1,
                "id": 101,
                "name": "Diwali Service Camp 2026",
                "agent_name": "Daksh Honda - Udaipur Service Reminder",
                "creator_name": "rajesh.admin (Main Admin)",
                "total_leads": 150,
                "answered": 118,
                "missed": 32,
                "ans_pct": 78.7,
                "status": "COMPLETED",
                "current_stage": "Completed (All 3 Stages)",
            },
            {
                "index": 2,
                "id": 102,
                "name": "StayVista Winter Villa Promotion",
                "agent_name": "StayVista Villa Assistant",
                "creator_name": "priya.marketing (Sub-user)",
                "total_leads": 85,
                "answered": 64,
                "missed": 21,
                "ans_pct": 75.3,
                "status": "IN PROGRESS",
                "current_stage": "Stage 2",
            },
            {
                "index": 3,
                "id": 103,
                "name": "Skoda Periodic Maintenance Campaign",
                "agent_name": "stellar_skoda",
                "creator_name": "amit.operations (Main Admin)",
                "total_leads": 210,
                "answered": 162,
                "missed": 48,
                "ans_pct": 77.1,
                "status": "COMPLETED",
                "current_stage": "Completed (All 3 Stages)",
            },
            {
                "index": 4,
                "id": 104,
                "name": "Samsung Appliance Customer Follow-up",
                "agent_name": "vtech_samsung",
                "creator_name": "vtech.support (Sub-user)",
                "total_leads": 130,
                "answered": 95,
                "missed": 35,
                "ans_pct": 73.1,
                "status": "COMPLETED",
                "current_stage": "Completed (All 3 Stages)",
            },
        ]
        total_campaign_leads = sum(c["total_leads"] for c in campaigns_list)
        total_campaign_answered = sum(c["answered"] for c in campaigns_list)
        total_campaign_missed = sum(c["missed"] for c in campaigns_list)
    else:
        campaigns_qs = SarvamCampaign.objects.filter(created_at__range=(t_min, t_max)).order_by("id")
        for idx, c in enumerate(campaigns_qs, start=1):
            creator_name = (
                f"{c.created_by.username} (Sub-user)" if (c.created_by and hasattr(c.created_by, 'profile') and c.created_by.profile.created_by)
                else (c.created_by.username if c.created_by else "Main Admin")
            )
            agent_name = c.sarvam_agent.name if c.sarvam_agent else "Default Agent"
        
            # Calculate percentage answered
            ans_pct = round((c.answered_count / max(1, c.total_leads)) * 100, 1)

            total_campaign_leads += c.total_leads
            total_campaign_answered += c.answered_count
            total_campaign_missed += c.missed_count

            campaigns_list.append({
                "index": idx,
                "id": c.id,
                "name": c.name,
                "agent_name": agent_name,
                "creator_name": creator_name,
                "total_leads": c.total_leads,
                "answered": c.answered_count,
                "missed": c.missed_count,
                "ans_pct": ans_pct,
                "status": c.status.replace("_", " "),
                "current_stage": f"Stage {c.current_stage}" if c.status != "COMPLETED" else "Completed (All 3 Stages)",
            })

    # 2. Fetch Agents & Quota Status
    agents_qs = SarvamAgent.objects.filter(is_active=True).order_by("name")
    agents_list = []
    
    for ag in agents_qs:
        # Today's billed seconds for this agent
        today_billed_sec = ag.call_records.filter(created_at__range=(t_min, t_max)).aggregate(tot=Sum('billed_seconds'))['tot'] or 0
        today_used_mins = round(today_billed_sec / 60.0, 1)
        
        rem_mins = ag.remaining_minutes
        alloc_mins = round(float(ag.allocated_minutes), 1)

        if ag.is_minutes_exhausted:
            quota_status = "EXHAUSTED"
            status_color = "#dc2626"  # Red
            status_bg = "#fef2f2"
        elif rem_mins < 100:
            quota_status = "LOW BALANCE"
            status_color = "#d97706"  # Amber
            status_bg = "#fffbeb"
        else:
            quota_status = "HEALTHY"
            status_color = "#16a34a"  # Green
            status_bg = "#f0fdf4"

        agents_list.append({
            "name": ag.name,
            "phone": ag.agent_phone or "N/A",
            "allocated_mins": alloc_mins,
            "today_used_mins": today_used_mins,
            "remaining_mins": rem_mins,
            "quota_status": quota_status,
            "status_color": status_color,
            "status_bg": status_bg,
        })

    # 3. Overall Daily Telephony Metrics (all calls today: inbound, outbound, campaigns)
    if dummy:
        total_calls_count = total_campaign_leads + 45
        total_answered_calls = total_campaign_answered + 38
        overall_ans_pct = round((total_answered_calls / max(1, total_calls_count)) * 100, 1)
        total_billed_minutes_today = 342.5
    else:
        all_calls_today = SarvamCallRecord.objects.filter(created_at__range=(t_min, t_max))
        total_calls_count = all_calls_today.count()
        total_answered_calls = all_calls_today.exclude(
            status__in=["NO_ANSWER", "MISSED", "FAILED", "BUSY", "CANCELLED", "DIALING", "PENDING", "UNANSWERED", "TIMEOUT"]
        ).count()
        overall_ans_pct = round((total_answered_calls / max(1, total_calls_count)) * 100, 1)
        total_billed_seconds_today = all_calls_today.aggregate(tot=Sum('billed_seconds'))['tot'] or 0
        total_billed_minutes_today = round(total_billed_seconds_today / 60.0, 1)

    # 4. Generate HTML Email Body
    html_content = _build_html_email_template(
        date_str=date_display_str,
        campaigns=campaigns_list,
        agents=agents_list,
        total_campaigns=len(campaigns_list),
        total_leads=total_campaign_leads,
        total_answered=total_campaign_answered,
        total_missed=total_campaign_missed,
        total_calls_count=total_calls_count,
        total_billed_minutes=total_billed_minutes_today,
        overall_ans_pct=overall_ans_pct,
        generated_at=now_ist.strftime("%d %b %Y, %I:%M %p IST")
    )

    plain_content = _build_plain_text_summary(
        date_str=date_display_str,
        campaigns=campaigns_list,
        agents=agents_list,
        total_campaigns=len(campaigns_list),
        total_leads=total_campaign_leads,
        total_answered=total_campaign_answered,
        total_billed_minutes=total_billed_minutes_today
    )

    subject = f"📊 [DEMO / DUMMY TEST] JMS Voice Bot — Daily Campaign & Telephony Summary ({date_display_str})" if dummy else f"📊 JMS Voice Bot — Daily Campaign & Telephony Summary ({date_display_str})"
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'JMS Tech Solution <voiceagents@jmstech.co>')

    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=recipients
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send(fail_silently=False)

        # Update last sent date
        config.last_sent_date = target_date
        config.save(update_fields=["last_sent_date"])

        logger.info(f"✅ [DAILY SUMMARY EMAIL SENT]: Sent daily summary for {date_display_str} to {len(recipients)} recipients ({', '.join(recipients)}).")
        return {
            "status": "success",
            "message": f"Daily summary email successfully sent to {len(recipients)} recipient(s).",
            "recipients": recipients,
            "target_date": str(target_date),
            "campaigns_count": len(campaigns_list)
        }
    except Exception as e:
        logger.error(f"❌ [DAILY SUMMARY EMAIL ERROR]: Failed to send daily summary: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}",
            "recipients": recipients
        }


def _build_html_email_template(date_str, campaigns, agents, total_campaigns, total_leads, total_answered, total_missed, total_calls_count, total_billed_minutes, overall_ans_pct, generated_at):
    """Builds a responsive, executive-styled HTML email."""

    # Build Campaigns Rows
    if campaigns:
        campaign_rows = ""
        for c in campaigns:
            status_style = "color:#16a34a; font-weight:600;" if "COMPLETED" in c["status"] else ("color:#dc2626;" if "CANCELLED" in c["status"] else "color:#2563eb; font-weight:600;")
            campaign_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0; font-size: 13px;">
                <td style="padding: 12px 10px; font-weight: 600; color: #1e293b;">#{c['id']}</td>
                <td style="padding: 12px 10px; font-weight: 600; color: #0284c7;">{c['name']}</td>
                <td style="padding: 12px 10px; color: #334155;">{c['agent_name']}</td>
                <td style="padding: 12px 10px; color: #64748b;">{c['creator_name']}</td>
                <td style="padding: 12px 10px; text-align: center; font-weight: 600; color: #1e293b;">{c['total_leads']}</td>
                <td style="padding: 12px 10px; text-align: center; color: #16a34a; font-weight: 600;">{c['answered']} <span style="font-size:11px; color:#64748b;">({c['ans_pct']}%)</span></td>
                <td style="padding: 12px 10px; text-align: center; color: #ef4444;">{c['missed']}</td>
                <td style="padding: 12px 10px; {status_style}">{c['status']}</td>
            </tr>
            """
    else:
        campaign_rows = """
        <tr>
            <td colspan="8" style="padding: 24px; text-align: center; color: #64748b; font-size: 13px; background: #f8fafc;">
                <em>No Excel campaigns were executed on this date. Individual call and agent balance telemetry are detailed below.</em>
            </td>
        </tr>
        """

    # Build Agent Quota Rows
    agent_rows = ""
    for ag in agents:
        agent_rows += f"""
        <tr style="border-bottom: 1px solid #e2e8f0; font-size: 13px;">
            <td style="padding: 12px 10px; font-weight: 600; color: #1e293b;">{ag['name']}</td>
            <td style="padding: 12px 10px; color: #64748b; font-family: monospace;">{ag['phone']}</td>
            <td style="padding: 12px 10px; text-align: right; color: #334155;">{ag['allocated_mins']}m</td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 600; color: #0284c7;">{ag['today_used_mins']}m</td>
            <td style="padding: 12px 10px; text-align: right; font-weight: 700; color: #0f172a;">{ag['remaining_mins']}m</td>
            <td style="padding: 12px 10px; text-align: center;">
                <span style="display:inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background:{ag['status_bg']}; color:{ag['status_color']};">
                    {ag['quota_status']}
                </span>
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>JMS Voice Bot Daily Summary</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f1f5f9; padding: 30px 10px;">
            <tr>
                <td align="center">
                    <table width="100%" cellpadding="0" cellspacing="0" style="max-width: 780px; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 32px 30px; border-bottom: 3px solid #0284c7;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td>
                                            <span style="display: inline-block; background: rgba(2, 132, 199, 0.2); border: 1px solid #0284c7; color: #38bdf8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; padding: 4px 12px; border-radius: 9999px; margin-bottom: 8px;">
                                                Automated End-Of-Day Report
                                            </span>
                                            <h1 style="margin: 0; font-size: 22px; color: #ffffff; font-weight: 700; letter-spacing: -0.5px;">
                                                Daily Campaign & Telephony Summary
                                            </h1>
                                            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 14px;">
                                                Activity Date: <strong style="color: #f8fafc;">{date_str}</strong> (IST)
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- KPI Highlights -->
                        <tr>
                            <td style="padding: 24px 30px 16px 30px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td width="25%" style="padding: 6px;">
                                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 12px; text-align: center;">
                                                <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px;">Campaigns</div>
                                                <div style="font-size: 24px; font-weight: 800; color: #0f172a; margin-top: 4px;">{total_campaigns}</div>
                                            </div>
                                        </td>
                                        <td width="25%" style="padding: 6px;">
                                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 12px; text-align: center;">
                                                <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px;">Campaign Leads</div>
                                                <div style="font-size: 24px; font-weight: 800; color: #0284c7; margin-top: 4px;">{total_leads}</div>
                                            </div>
                                        </td>
                                        <td width="25%" style="padding: 6px;">
                                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 12px; text-align: center;">
                                                <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px;">Answer Rate</div>
                                                <div style="font-size: 24px; font-weight: 800; color: #16a34a; margin-top: 4px;">{overall_ans_pct}%</div>
                                            </div>
                                        </td>
                                        <td width="25%" style="padding: 6px;">
                                            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 12px; text-align: center;">
                                                <div style="font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; letter-spacing: 0.5px;">Total Mins Billed</div>
                                                <div style="font-size: 24px; font-weight: 800; color: #8b5cf6; margin-top: 4px;">{total_billed_minutes}m</div>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Section 1: Campaigns Breakdown -->
                        <tr>
                            <td style="padding: 16px 30px;">
                                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #0f172a; font-weight: 700; display: flex; align-items: center;">
                                    🚀 Today's Excel Calling Campaigns
                                </h3>
                                <div style="overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 12px;">
                                    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; text-align: left;">
                                        <thead>
                                            <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; text-transform: uppercase; color: #64748b;">
                                                <th style="padding: 10px;">ID</th>
                                                <th style="padding: 10px;">Campaign Name</th>
                                                <th style="padding: 10px;">Voice Agent</th>
                                                <th style="padding: 10px;">Launched By</th>
                                                <th style="padding: 10px; text-align: center;">Leads</th>
                                                <th style="padding: 10px; text-align: center;">Answered</th>
                                                <th style="padding: 10px; text-align: center;">Missed</th>
                                                <th style="padding: 10px;">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {campaign_rows}
                                        </tbody>
                                    </table>
                                </div>
                            </td>
                        </tr>

                        <!-- Section 2: Agent Quota & Balance -->
                        <tr>
                            <td style="padding: 20px 30px;">
                                <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #0f172a; font-weight: 700;">
                                    ⏱️ Voice Agent Minute Allocation & Live Balance
                                </h3>
                                <div style="overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 12px;">
                                    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse; text-align: left;">
                                        <thead>
                                            <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; font-size: 11px; text-transform: uppercase; color: #64748b;">
                                                <th style="padding: 10px;">Agent Name</th>
                                                <th style="padding: 10px;">Virtual DID</th>
                                                <th style="padding: 10px; text-align: right;">Total Allocated</th>
                                                <th style="padding: 10px; text-align: right;">Used Today</th>
                                                <th style="padding: 10px; text-align: right;">Remaining Balance</th>
                                                <th style="padding: 10px; text-align: center;">Quota Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {agent_rows}
                                        </tbody>
                                    </table>
                                </div>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background: #f8fafc; padding: 20px 30px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td>
                                            Report generated on: <strong>{generated_at}</strong><br>
                                            System: <em>JMS Voice Bot SaaS — Multi-Tenant Platform</em>
                                        </td>
                                        <td align="right" style="color: #94a3b8;">
                                            To edit recipient emails, update in <strong>Django Admin &gt; Daily Summary Email Config</strong>.
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def _build_plain_text_summary(date_str, campaigns, agents, total_campaigns, total_leads, total_answered, total_billed_minutes):
    """Fallback plain-text summary."""
    lines = [
        f"JMS VOICE BOT — DAILY SUMMARY ({date_str})",
        "=" * 60,
        f"Campaigns Run: {total_campaigns} | Total Leads: {total_leads} | Total Answered: {total_answered} | Total Minutes Billed: {total_billed_minutes}m",
        "",
        "CAMPAIGNS BREAKDOWN:",
        "-" * 60
    ]
    if campaigns:
        for c in campaigns:
            lines.append(f"• Campaign #{c['id']}: {c['name']} | Agent: {c['agent_name']} | By: {c['creator_name']} | Leads: {c['total_leads']} | Answered: {c['answered']} ({c['ans_pct']}%) | Status: {c['status']}")
    else:
        lines.append("No Excel campaigns run today.")

    lines.extend([
        "",
        "AGENT MINUTE BALANCES:",
        "-" * 60
    ])
    for ag in agents:
        lines.append(f"• {ag['name']} ({ag['phone']}): Remaining: {ag['remaining_mins']}m | Used Today: {ag['today_used_mins']}m | Quota: {ag['quota_status']}")

    lines.append("\nGenerated automatically by JMS Voice Bot SaaS.")
    return "\n".join(lines)

