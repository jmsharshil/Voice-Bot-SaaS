import os

path = 'conversations/services/core/behavior_router.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_fn = """def get_role_strategy(role_name: str):
    if not role_name:
        return "automobile"
    role_lower = role_name.lower()
    if ("icemake" in role_lower or "ice make" in role_lower) and ("v2" in role_lower or "2" in role_lower):
        return "icemake_v2"
    if "icemake" in role_lower or "ice make" in role_lower:
        return "icemake"
    if "raahi" in role_lower:
        return "raahi_iiiem_strategy"
    if "priya" in role_name.lower():
        return "priya_naavya_strategy"
    return ROLE_STRATEGY_MAP.get(role_name, "automobile")"""

new_fn = """def get_role_strategy(role_name: str, agent_name: str = ""):
    combined = f"{role_name or ''} {agent_name or ''}".strip().lower()
    if not combined:
        return "automobile"
    if ("icemake" in combined or "ice make" in combined) and ("v2" in combined or "2" in combined):
        return "icemake_v2"
    if "icemake" in combined or "ice make" in combined:
        return "icemake"
    if "raahi" in combined:
        return "raahi_iiiem_strategy"
    if "priya" in combined:
        return "priya_naavya_strategy"
    return ROLE_STRATEGY_MAP.get(role_name, "automobile")"""

content_normalized = content.replace('\r\n', '\n')
if old_fn in content_normalized:
    updated = content_normalized.replace(old_fn, new_fn)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print("SUCCESS: Updated behavior_router.py")
else:
    print("ERROR: old_fn not found")

