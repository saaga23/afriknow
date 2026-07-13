# Cost calculation for expanded GM-only runs
# Based on actual v17 costs per model

v17_costs = {
    'Claude Sonnet 4.6':     {'items': 180, 'calls': 1260, 'cost': 1.0879, 'provider': 'openrouter'},
    'DeepSeek-V3.2':        {'items': 180, 'calls': 1260, 'cost': 0.0707, 'provider': 'openrouter'},
    'Gemini 2.5 Flash Lite':{'items': 180, 'calls': 1260, 'cost': 0.0312, 'provider': 'openrouter'},
    'Gemma-4-31B':          {'items': 180, 'calls': 1260, 'cost': 0.0397, 'provider': 'openrouter'},
    'GPT-4o-mini':          {'items': 180, 'calls': 1260, 'cost': 0.0470, 'provider': 'openrouter'},
    'GPT-4.1 Nano':         {'items': 180, 'calls': 1267, 'cost': 0.0316, 'provider': 'openrouter'},
    'Llama-3.3-70B':        {'items': 180, 'calls': 1260, 'cost': 0.0326, 'provider': 'openrouter'},
}

def estimate(target_items):
    scale = target_items / 180
    print(f"=== {target_items}-item GM-only run cost estimate ===")
    print(f"Scale factor: {scale:.2f}x")
    print()
    openrouter_total = 0
    modal_total = 0
    for model, data in v17_costs.items():
        estimated = data['cost'] * scale
        provider = data['provider']
        print(f"  {model}: ${estimated:.2f} ({provider})")
        if provider == 'modal':
            modal_total += estimated
        else:
            openrouter_total += estimated
    print()
    print(f"OpenRouter total (all 7): ${openrouter_total:.2f}")
    print(f"With Modal for open-weight: ~${openrouter_total * 0.3:.2f} (70% savings on open models)")

for n in [300, 500, 750, 1000]:
    estimate(n)
    print()
