from conversations.models import SarvamCallRecord, SarvamAgent, SarvamCampaignLead, SarvamCampaign

vtech = SarvamAgent.objects.filter(slug="vtech").first()
print(f"Agent: {vtech.name if vtech else 'NOT FOUND'}")

if vtech:
    c, _ = SarvamCallRecord.objects.filter(sarvam_agent=vtech).delete()
    print(f"Deleted {c} SarvamCallRecord(s)")

    l, _ = SarvamCampaignLead.objects.filter(campaign__sarvam_agent=vtech).delete()
    print(f"Deleted {l} SarvamCampaignLead(s)")

    camps = SarvamCampaign.objects.filter(sarvam_agent=vtech)
    camps.update(
        status="pending", current_stage=1,
        stage_1_dispatched=0, stage_1_answered=0, stage_1_missed=0,
        stage_2_dispatched=0, stage_2_answered=0, stage_2_missed=0,
        stage_3_dispatched=0, stage_3_answered=0, stage_3_missed=0,
        answered_count=0, missed_count=0
    )
    print(f"Reset {camps.count()} campaign(s) to pending")
    print("vtech dashboard cleared!")
