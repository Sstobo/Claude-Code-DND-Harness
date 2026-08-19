# 🔍 WORLD CHECK - Campaign Consistency Validator

This command validates your generated world for completeness and consistency. Run after world generation or when debugging issues.

---

## PHASE 1: STRUCTURAL VALIDATION

### Step 0: Get Active Campaign Path
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
echo "Checking campaign: $(bash tools/gm-campaign.sh active)"
echo "Path: $CAMPAIGN_DIR"
```

### Step 1: Run Schema Validator (Preferred)
```bash
# Validates the active campaign against lib/schemas.py
uv run python lib/schemas.py
```

### Step 2: Check Session Log
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
if [ -f "$CAMPAIGN_DIR/session-log.md" ]; then
    lines=$(wc -l < "$CAMPAIGN_DIR/session-log.md")
    if [ $lines -gt 3 ]; then
        echo "✅ session-log.md - Has content ($lines lines)"
    else
        echo "⚠️ session-log.md - Minimal content"
    fi
else
    echo "❌ session-log.md - Missing"
fi
```

---

## PHASE 2: CONTENT VALIDATION

### Step 1: Campaign Overview Completeness
Covered by the schema validator above. Only add custom checks here if needed.

### Step 2: Location Analysis
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
with open(f'{campaign_dir}/locations.json', 'r') as f:
    locations = json.load(f)

print(f'📍 LOCATIONS: {len(locations)} total')

# Check for descriptions and connections
for name, data in locations.items():
    desc_len = len(data.get('description', ''))
    conn_count = len(data.get('connections', []))

    status = '✅' if desc_len > 50 else '⚠️'
    print(f'{status} {name}: {desc_len} chars, {conn_count} connections')

    # Check for orphaned locations
    if conn_count == 0:
        print(f'   ⚠️ No connections - orphaned location!')
" "$CAMPAIGN_DIR"
```

### Step 3: NPC Analysis
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
with open(f'{campaign_dir}/npcs.json', 'r') as f:
    npcs = json.load(f)

print(f'🎭 NPCS: {len(npcs)} total')

for name, data in npcs.items():
    desc_len = len(data.get('description', ''))
    tags = data.get('tags', {})

    # Check description length
    desc_status = '✅' if desc_len > 80 else '⚠️'

    # Check tags
    location_tags = tags.get('locations', [])
    quest_tags = tags.get('quests', [])

    print(f'{desc_status} {name}:')
    print(f'   Description: {desc_len} chars')
    print(f'   Attitude: {data.get(\"attitude\", \"unknown\")}')
    if location_tags:
        print(f'   📍 Locations: {location_tags}')
    if quest_tags:
        print(f'   📜 Quests: {quest_tags}')
" "$CAMPAIGN_DIR"
```

### Step 4: Plot Structure Check
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
with open(f'{campaign_dir}/facts.json', 'r') as f:
    facts = json.load(f)

print('📜 PLOT STRUCTURE:')

# Check for three-tier plots
plot_categories = ['plot_local', 'plot_regional', 'plot_world']
for category in plot_categories:
    if category in facts:
        count = len(facts[category])
        print(f'✅ {category}: {count} facts')
    else:
        print(f'❌ {category}: Missing')

# Check for other fact categories
other_categories = [k for k in facts.keys() if 'plot_' not in k]
if other_categories:
    print(f'📚 Other fact categories: {other_categories}')
" "$CAMPAIGN_DIR"
```

### Step 5: Consequences Timeline
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
with open(f'{campaign_dir}/consequences.json', 'r') as f:
    data = json.load(f)

active = data.get('active', [])
resolved = data.get('resolved', [])

print(f'⏰ CONSEQUENCES:')
print(f'   Active: {len(active)}')
print(f'   Resolved: {len(resolved)}')

if active:
    print('\\n   Scheduled Events:')
    for cons in active:
        trigger = cons.get('trigger', 'unknown')
        desc = cons.get('consequence', '')[:50]
        print(f'   • {trigger}: {desc}...')
" "$CAMPAIGN_DIR"
```

---

## PHASE 3: RELATIONSHIP VALIDATION

### Step 1: Location Connectivity
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
with open(f'{campaign_dir}/locations.json', 'r') as f:
    locations = json.load(f)

print('🔗 LOCATION CONNECTIONS:')

# Build connection graph
connections = {}
for name, data in locations.items():
    connections[name] = []
    for conn in data.get('connections', []):
        target = conn.get('to', '')
        if target:
            connections[name].append(target)
            # Check if target exists
            if target not in locations:
                print(f'❌ {name} connects to non-existent {target}')

# Find orphaned locations
orphaned = [name for name, conns in connections.items() if len(conns) == 0]
if orphaned:
    print(f'⚠️ Orphaned locations (no connections): {orphaned}')
else:
    print('✅ All locations connected')
" "$CAMPAIGN_DIR"
```

### Step 2: NPC Location Verification
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
with open(f'{campaign_dir}/npcs.json', 'r') as f:
    npcs = json.load(f)
with open(f'{campaign_dir}/locations.json', 'r') as f:
    locations = json.load(f)

print('🏠 NPC LOCATION TAGS:')

location_names = list(locations.keys())
issues = []

for name, data in npcs.items():
    location_tags = data.get('tags', {}).get('locations', [])
    if not location_tags:
        issues.append(f'⚠️ {name} has no location tags')
    else:
        # Verify locations exist
        for tag in location_tags:
            # Tags might be slugified versions of location names
            # This is a loose check - adjust based on your tagging convention
            pass  # For now, just note they have tags

if issues:
    for issue in issues[:5]:  # Show first 5 issues
        print(issue)
else:
    print('✅ All NPCs have location tags')
" "$CAMPAIGN_DIR"
```

---

## PHASE 4: COMPLETENESS REPORT

### Generate Summary Report
```bash
CAMPAIGN_DIR=$(bash tools/gm-campaign.sh path)
echo "
═══════════════════════════════════════════════════════
                 WORLD VALIDATION REPORT
═══════════════════════════════════════════════════════
Campaign: $(bash tools/gm-campaign.sh active)
"

# Quick stats
echo "📊 QUICK STATS:"
echo "   Locations: $(uv run python -c "import json; print(len(json.load(open('$CAMPAIGN_DIR/locations.json'))))")"
echo "   NPCs: $(uv run python -c "import json; print(len(json.load(open('$CAMPAIGN_DIR/npcs.json'))))")"
echo "   Active Plots: $(uv run python -c "import json; f=json.load(open('$CAMPAIGN_DIR/facts.json')); print(len([k for k in f.keys() if 'plot_' in k]))")"
echo "   Consequences: $(uv run python -c "import json; print(len(json.load(open('$CAMPAIGN_DIR/consequences.json')).get('active', [])))")"

echo "
🎯 READINESS CHECKLIST:
"

# Campaign ready check
uv run python -c "
import json
import sys

campaign_dir = sys.argv[1]
ready = True
issues = []

# Check campaign overview
with open(f'{campaign_dir}/campaign-overview.json', 'r') as f:
    campaign = json.load(f)
    if not campaign.get('campaign_name'):
        issues.append('❌ No campaign name set')
        ready = False
    if not campaign.get('player_position', {}).get('current_location'):
        issues.append('❌ No starting location set')
        ready = False

# Check minimum content
with open(f'{campaign_dir}/locations.json', 'r') as f:
    if len(json.load(f)) < 3:
        issues.append('❌ Less than 3 locations')
        ready = False

with open(f'{campaign_dir}/npcs.json', 'r') as f:
    if len(json.load(f)) < 4:
        issues.append('❌ Less than 4 NPCs')
        ready = False

if issues:
    print('\\n'.join(issues))
else:
    print('✅ World is ready for play!')
    print('✅ Run /gm to begin!')
" "$CAMPAIGN_DIR"
```

---

## QUICK FIX COMMANDS

Based on validation results, here are quick fixes:

### Orphaned Locations
```bash
# Connect orphaned location to nearest
bash tools/gm-location.sh connect "[Orphaned]" "[Nearby Location]" "a winding path"
```

### Missing Descriptions
```bash
# Use world-builder agent to enhance
# Launch with Task tool targeting specific location/NPC
```

### No Plot Facts
```bash
# Quick plot generation
bash tools/gm-note.sh "plot_local" "Strange disappearances plague the town at night"
bash tools/gm-note.sh "plot_regional" "Ancient seals are weakening across the land"
bash tools/gm-note.sh "plot_world" "The Dark Star approaches, heralding change"
```

---

## SUCCESS CRITERIA

Your world is ready when:
- ✅ All files valid JSON
- ✅ Campaign overview complete
- ✅ Starting location defined
- ✅ 4+ locations with descriptions
- ✅ All locations connected
- ✅ 4+ NPCs with descriptions and attitudes
- ✅ Three-tier plot structure
- ✅ 2+ active consequences
- ✅ Session log initialized

---

Run this check after world generation and before starting play!
