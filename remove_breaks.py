import re

with open("generate_flow_audio.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove every  <break time='Xms'/> tag (with any surrounding whitespace / quotes)
before = content.count("<break")
content = re.sub(r"\s*<break time='[^']*'/>\s*", " ", content)
after = content.count("<break")

with open("generate_flow_audio.py", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Done. Removed {before - after} <break> tags.")
