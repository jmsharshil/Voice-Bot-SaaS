import os

for path in ['conversations/consumers_service2.py', 'conversations/consumers.py']:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # In get_agent_strategy:
    target1 = 'return get_role_strategy(role_name)'
    replacement1 = 'return get_role_strategy(role_name, agent.name or "")'

    # In get_initial_call_data:
    target2 = 'strategy_key = get_role_strategy(role_name)'
    replacement2 = 'strategy_key = get_role_strategy(role_name, agent.name or "")'

    updated = content.replace(target1, replacement1).replace(target2, replacement2)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(updated)
    print(f"Updated {path}")

