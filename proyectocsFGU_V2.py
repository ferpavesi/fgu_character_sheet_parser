"""
Fantasy Grounds Unity Character Sheet Parser - Web Version
===========================================================
Flask web application for converting FGU XML character files to HTML.
Deploy on Vercel, Heroku, or any WSGI-compatible server.

Usage (Local):
    pip install flask werkzeug
    python proyectocsFGU_V2.py

Usage (Vercel):
    vercel deploy
"""

import xml.etree.ElementTree as ET
from html import escape
import os
from io import BytesIO
from flask import Flask, render_template_string, request, send_file, jsonify
from werkzeug.utils import secure_filename

# Create Flask app - must be at module level for Vercel
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file
app.config['UPLOAD_FOLDER'] = '/tmp'


def safe_get_text(element, path, default=""):
    """Safely get text from XML element, return default if not found."""
    if element is None:
        return default
    sub = element.find(path)
    return sub.text if sub is not None and sub.text else default


def formatted_html(element):
    """Return inner HTML for Fantasy Grounds formattedtext elements."""
    if element is None:
        return ""
    parts = []
    text = (element.text or "").strip()
    if text:
        parts.append(text)
    for child in element:
        parts.append(ET.tostring(child, encoding='unicode', method='html'))
    html_str = ''.join(parts).strip()
    
    # Remove duplicate paragraphs (common in FGU exports)
    lines = html_str.split('\n')
    seen = set()
    unique_lines = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped and line_stripped in seen:
            continue
        if line_stripped:
            seen.add(line_stripped)
        unique_lines.append(line)
    
    return '\n'.join(unique_lines).strip()


def format_modifier(value):
    """Format ability modifier with + sign if positive."""
    try:
        val = int(value)
        return f"+{val}" if val >= 0 else str(val)
    except:
        return value


def get_proficiency_bonus(level):
    """Calculate proficiency bonus based on character level."""
    try:
        lvl = int(level)
        return 2 + ((lvl - 1) // 4)
    except:
        return 2


def escape_html(text):
    """Escape HTML special characters."""
    if not text:
        return ""
    return escape(str(text))


def parse_fgu_character_to_html(xml_content):
    """Parse FGU character XML and return HTML character sheet."""
    try:
        # Parse XML from bytes
        root = ET.fromstring(xml_content)
        char = root.find("character")

        if char is None:
            return None, "Error: No character data found in XML"
        
        # Extract basic info
        name = safe_get_text(char, "name")
        race = safe_get_text(char, "race")
        subrace = safe_get_text(char, "subrace")
        alignment = safe_get_text(char, "alignment")
        background = safe_get_text(char, "background")
        gender = safe_get_text(char, "gender")
        age = safe_get_text(char, "age")
        
        # Calculate total level
        total_level = 0
        classes_info = []
        classes_elem = char.find("classes")
        for cls in (classes_elem if classes_elem is not None else []):
            cls_name = safe_get_text(cls, "name")
            cls_level = safe_get_text(cls, "level")
            cls_spec = safe_get_text(cls, "specialization")
            try:
                total_level += int(cls_level)
            except:
                pass
            classes_info.append({
                "name": cls_name,
                "level": cls_level,
                "specialization": cls_spec
            })
        
        prof_bonus = get_proficiency_bonus(total_level)
        
        # Extract abilities
        abilities = {}
        ability_names = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        for abil_name in ability_names:
            abil_elem = char.find(f"abilities/{abil_name}")
            if abil_elem is not None:
                abilities[abil_name] = {
                    "score": safe_get_text(abil_elem, "score"),
                    "bonus": safe_get_text(abil_elem, "bonus"),
                    "save": safe_get_text(abil_elem, "save"),
                    "saveprof": safe_get_text(abil_elem, "saveprof", "0") == "1"
                }
        
        # Extract HP
        hp_elem = char.find("hp")
        hp_total = safe_get_text(hp_elem, "total") if hp_elem is not None else "0"
        hp_wounds = safe_get_text(hp_elem, "wounds") if hp_elem is not None else "0"
        hp_temp = safe_get_text(hp_elem, "temporary") if hp_elem is not None else "0"
        
        hp_wounds = str(hp_wounds).strip()
        hp_temp = str(hp_temp).strip()
        
        # Extract AC
        ac_elem = char.find("defenses/ac")
        ac_total = safe_get_text(ac_elem, "total") if ac_elem is not None else "10"
        
        # Extract Speed
        speed_elem = char.find("speed")
        speed_total = safe_get_text(speed_elem, "total") if speed_elem is not None else "30"
        
        # Extract Initiative
        init_elem = char.find("initiative")
        initiative = safe_get_text(init_elem, "total") if init_elem is not None else ""
        if not initiative and "dexterity" in abilities:
            initiative = abilities["dexterity"]["bonus"]
        
        # Extract Skills
        skills = []
        skill_elem = char.find("skilllist")
        if skill_elem is not None:
            for skill in skill_elem:
                skill_name = safe_get_text(skill, "name")
                skill_total = safe_get_text(skill, "total")
                skill_prof = safe_get_text(skill, "prof", "0") == "1"
                skill_stat = safe_get_text(skill, "stat")
                skills.append({
                    "name": skill_name,
                    "total": skill_total,
                    "prof": skill_prof,
                    "stat": skill_stat
                })
        
        skills.sort(key=lambda x: x["name"])
        
        # Extract Features
        features = []
        feature_elem = char.find("featurelist")
        if feature_elem is not None:
            for feature in feature_elem:
                feat_name = safe_get_text(feature, "name")
                feat_level = safe_get_text(feature, "level")
                features.append({
                    "name": feat_name,
                    "level": feat_level
                })
        
        # Extract Feats
        feats = []
        feat_elem = char.find("featlist")
        if feat_elem is not None:
            for feat in feat_elem:
                feat_name = safe_get_text(feat, "name")
                feat_category = safe_get_text(feat, "category")
                feat_level = safe_get_text(feat, "level")
                feats.append({
                    "name": feat_name,
                    "category": feat_category,
                    "level": feat_level
                })
        
        # Extract Inventory
        inventory = []
        inv_elem = char.find("inventorylist")
        if inv_elem is not None:
            for item in inv_elem:
                item_name = safe_get_text(item, "name")
                item_count = safe_get_text(item, "count", "1")
                item_cost = safe_get_text(item, "cost", "")
                inventory.append({
                    "name": item_name,
                    "count": item_count,
                    "cost": item_cost
                })
        
        # Extract Coins
        coins = {}
        coins_elem = char.find("coins")
        if coins_elem is not None:
            for coin in coins_elem:
                coin_name = safe_get_text(coin, "name")
                coin_amount = safe_get_text(coin, "amount", "0")
                coins[coin_name] = coin_amount
        
        # Extract Personality Traits, Ideals, Bonds, Flaws
        personality = safe_get_text(char, "personality")
        ideals = safe_get_text(char, "ideals")
        bonds = safe_get_text(char, "bonds")
        flaws = safe_get_text(char, "flaws")
        
        # Extract Spell Info
        spell_ability = ""
        spell_save_dc = ""
        spell_attack_bonus = ""
        classes_elem = char.find("classes")
        for cls in (classes_elem if classes_elem is not None else []):
            spell_abil = safe_get_text(cls, "spellability")
            if spell_abil:
                spell_ability = spell_abil
                break
        
        spellcasting_elem = char.find("spellcasting")
        if spellcasting_elem is not None:
            spell_save_dc = safe_get_text(spellcasting_elem, "saveDC")
            spell_attack_bonus = safe_get_text(spellcasting_elem, "attackbonus")
        
        # Extract Spells from powers section
        spells = []
        powers_elem = char.find("powers")
        if powers_elem is not None:
            for power in powers_elem:
                group = safe_get_text(power, "group", "")
                spell_level = safe_get_text(power, "level", "")
                spell_school = safe_get_text(power, "school", "")
                
                if ("Spells" in group or spell_school) and spell_level:
                    spell_name = safe_get_text(power, "name")
                    spell_prepared = safe_get_text(power, "prepared", "0")
                    spell_casting_time = safe_get_text(power, "castingtime", "")
                    spell_range = safe_get_text(power, "range", "")
                    spell_components = safe_get_text(power, "components", "")
                    spell_duration = safe_get_text(power, "duration", "")
                    spell_ritual = safe_get_text(power, "ritual", "0") == "1"
                    desc_elem = power.find("description")
                    spell_description = formatted_html(desc_elem)
                    
                    spells.append({
                        "name": spell_name,
                        "level": spell_level,
                        "prepared": spell_prepared,
                        "school": spell_school,
                        "casting_time": spell_casting_time,
                        "range": spell_range,
                        "components": spell_components,
                        "duration": spell_duration,
                        "ritual": spell_ritual,
                        "description": spell_description
                    })
        
        spells.sort(key=lambda x: (int(x["level"]) if x["level"].isdigit() else 99, x["name"]))
        
        # Extract Sorcery Points
        sorcery_points = {}
        powers_elem = char.find("powers")
        if powers_elem is not None:
            for power in powers_elem:
                power_name = safe_get_text(power, "name")
                if power_name == "Sorcery Points":
                    sorcery_max = safe_get_text(power, "prepared", "0")
                    sorcery_used = safe_get_text(power, "locked", "0")
                    if sorcery_max and sorcery_max != "0":
                        sorcery_points = {
                            "max": sorcery_max,
                            "used": sorcery_used
                        }
                    break
        
        # Extract Spell Slots
        spell_slots = {}
        powermeta_elem = char.find("powermeta")
        if powermeta_elem is not None:
            for slot_level in range(1, 10):
                slot_elem = powermeta_elem.find(f"spellslots{slot_level}")
                if slot_elem is not None:
                    max_slots = safe_get_text(slot_elem, "max", "0")
                    used_slots = safe_get_text(slot_elem, "used", "0")
                    if max_slots and max_slots != "0":
                        spell_slots[str(slot_level)] = {
                            "max": max_slots,
                            "used": used_slots
                        }
        
        # Build HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Character Sheet - {escape_html(name) if name else 'Unknown'}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        html {{
            font-size: 16px;
        }}
        
        body {{
            font-family: 'Book Antiqua', 'Palatino Linotype', Palatino, serif;
            background: linear-gradient(135deg, #f5f1e8 0%, #e8ddd4 100%);
            padding: 20px;
            color: #2c1810;
            line-height: 1.4;
            min-width: 280px;
            word-wrap: break-word;
            overflow-x: hidden;
        }}
        
        .character-sheet {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border: 3px solid #8b6914;
            border-radius: 8px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            padding: 25px;
            box-sizing: border-box;
            width: 100%;
        }}
        
        .header {{
            border-bottom: 3px solid #8b6914;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            color: #8b6914;
            text-align: center;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        
        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            font-size: 1.1em;
        }}
        
        .header-info div {{
            background: #f5f1e8;
            padding: 8px 12px;
            border-radius: 4px;
            border-left: 4px solid #8b6914;
        }}
        
        .header-info strong {{
            color: #8b6914;
            margin-right: 5px;
        }}
        
        .sidebar {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            width: 100%;
            min-width: 0;
        }}
        
        .stat-box {{
            background: #f5f1e8;
            border: 1px solid #8b6914;
            border-radius: 3px;
            padding: 3px;
            text-align: center;
            margin-bottom: 4px;
            min-width: 0;
            box-sizing: border-box;
            overflow-wrap: break-word;
            word-break: break-word;
        }}
        
        .stat-box h3 {{
            color: #8b6914;
            font-size: 0.7em;
            margin-bottom: 2px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        
        .ability-score {{
            font-size: 1.2em;
            font-weight: bold;
            color: #2c1810;
            margin: 2px 0;
        }}
        
        .ability-modifier {{
            font-size: 0.95em;
            color: #8b6914;
            font-weight: bold;
            margin: 2px 0;
        }}
        
        .save-box {{
            font-size: 0.85em;
            margin-top: 5px;
        }}
        
        .skill-item {{
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px dotted #ccc;
        }}
        
        .skill-item label {{
            display: flex;
            align-items: center;
            gap: 5px;
            cursor: pointer;
        }}
        
        .section {{
            background: #f5f1e8;
            border: 2px solid #8b6914;
            border-radius: 6px;
            padding: 15px;
        }}
        
        .section h2 {{
            color: #8b6914;
            font-size: 1.3em;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #8b6914;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .page {{
            background: white;
            border: 3px solid #8b6914;
            border-radius: 24px;
            padding: 30px 20px;
            margin: 30px auto;
            max-width: 900px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            box-sizing: border-box;
            width: 100%;
        }}
        
        .page-layout {{
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        
        .hp-box {{
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 4px;
            margin-bottom: 10px;
        }}
        
        .hp-box .hp-total {{
            font-size: 2em;
            font-weight: bold;
            color: #c12727;
        }}
        
        .hp-box .hp-current {{
            font-size: 1.5em;
            color: #2c1810;
        }}
        
        .hp-details {{
            display: flex;
            justify-content: space-around;
            margin-top: 10px;
            font-size: 0.9em;
        }}
        
        .features-list, .feats-list, .inventory-list {{
            list-style: none;
        }}
        
        .features-list li, .feats-list li {{
            padding: 6px 0;
            border-bottom: 1px dotted #ccc;
        }}
        
        .inventory-list li {{
            padding: 6px 0;
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px dotted #ccc;
            white-space: normal;
        }}
        
        .spell-slot-level {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 6px;
        }}
        
        .spell-slot-level strong {{
            min-width: 70px;
            font-size: 0.9em;
            color: #8b6914;
        }}
        
        .spell-slot-bubbles {{
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }}
        
        .spell-description {{
            font-size: 0.9em;
            color: #333;
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px dotted #ccc;
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: normal;
        }}
        
        .coins {{
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
            padding: 10px;
        }}
        
        .coin-item {{
            text-align: center;
            padding: 8px 15px;
            background: white;
            border-radius: 4px;
            border: 1px solid #8b6914;
        }}
        
        .coin-item .amount {{
            font-size: 1.3em;
            font-weight: bold;
            color: #8b6914;
            margin-top: 8px;
        }}
        
        .coin-item input[type="text"] {{
            width: 80px;
            padding: 6px;
            border: 1px solid #8b6914;
            border-radius: 3px;
            text-align: center;
            font-size: 1.1em;
            font-weight: bold;
            color: #8b6914;
            margin-top: 8px;
        }}
        
        .spell-level-toggle {{
            background: white;
            border: 2px solid #8b6914;
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 10px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            user-select: none;
            transition: background-color 0.2s;
        }}
        
        .spell-level-toggle:hover {{
            background-color: #f5f1e8;
        }}
        
        .spell-level-toggle h3 {{
            color: #8b6914;
            font-size: 1.1em;
            margin: 0;
        }}
        
        .spell-level-content {{
            display: none;
        }}
        
        .spell-level-content.active {{
            display: block;
        }}
        
        @media (max-width: 900px) {{
            body {{
                padding: 8px;
            }}
            
            .character-sheet {{
                padding: 10px;
                border: 2px solid #8b6914;
            }}
            
            .header h1 {{
                font-size: 1.3em;
                margin-bottom: 8px;
            }}
            
            .header-info {{
                grid-template-columns: 1fr;
                gap: 6px;
            }}
            
            .page-layout {{
                grid-template-columns: 1fr !important;
                gap: 12px !important;
            }}
            
            .stat-box {{
                padding: 2px 5px;
                margin-bottom: 2px;
            }}
            
            .section {{
                padding: 8px;
            }}
            
            .section h2 {{
                font-size: 1em;
                margin-bottom: 8px;
            }}
            
            .page {{
                border: 2px solid #8b6914;
                padding: 12px 8px;
                margin: 15px 0;
            }}
        }}
        
        @media (max-width: 600px) {{
            html {{
                font-size: 14px;
            }}
            
            body {{
                padding: 4px;
                margin: 0;
            }}
            
            .character-sheet {{
                padding: 6px;
                border: 1px solid #8b6914;
            }}
            
            .header h1 {{
                font-size: 1.1em;
                margin: 0;
            }}
            
            .page {{
                border: 1px solid #8b6914;
                padding: 8px;
                margin: 10px 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="character-sheet">
        <div class="header">
            <h1>{escape_html(name) if name else 'Character Name'}</h1>
            <div class="header-info">
"""
        
        if race:
            race_display = f"{race}"
            if subrace:
                race_display += f" ({subrace})"
            html += f'                <div><strong>Race:</strong> {escape_html(race_display)}</div>\n'
        
        if classes_info:
            classes_str = ", ".join([f"{c['name']} {c['level']}" for c in classes_info])
            html += f'                <div><strong>Class & Level:</strong> {escape_html(classes_str)}</div>\n'
        
        if background:
            html += f'                <div><strong>Background:</strong> {escape_html(background)}</div>\n'
        
        if alignment:
            html += f'                <div><strong>Alignment:</strong> {escape_html(alignment)}</div>\n'
        
        html += f'                <div><strong>Proficiency Bonus:</strong> {format_modifier(prof_bonus)}</div>\n'
        
        html += """            </div>
        </div>
        
        <div class="page">
            <div class="page-layout">
                <div class="sidebar">
"""
        
        # Ability Scores
        for abil_name in ability_names:
            abil_data = abilities.get(abil_name, {})
            abil_display = abil_name.capitalize()[:3].upper()
            score = abil_data.get("score", "10")
            bonus = abil_data.get("bonus", "0")
            save = abil_data.get("save", "0")
            is_prof = abil_data.get("saveprof", False)
            
            html += f"""                    <div class="stat-box">
                        <h3>{abil_display}</h3>
                        <div class="ability-score">{escape_html(score)}</div>
                        <div class="ability-modifier">{format_modifier(bonus)}</div>
                        <div class="save-box">
                            SAVE {format_modifier(save)} {'✓' if is_prof else ''}
                        </div>
                    </div>
"""
        
        # Skills
        html += """                    <div class="stat-box">
                        <h3>Skills</h3>
                        <div style="text-align: left; font-size: 0.85em;">
"""
        
        for skill in skills:
            prof_indicator = "●" if skill["prof"] else "○"
            html += f"""                            <div class="skill-item">
                                <span>{prof_indicator} {escape_html(skill['name'])}</span>
                                <span>{format_modifier(skill['total'])}</span>
                            </div>
"""
        
        html += """                        </div>
                    </div>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div class="section">
                        <h2>Hit Points</h2>
                        <div class="hp-box">
                            <div class="hp-total">""" + escape_html(str(hp_total)) + """</div>
                            <div class="hp-current">Current HP</div>
                            <div class="hp-details">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span>Wounds:</span>
                                    <input type="text" value='""" + hp_wounds + """' style="width: 60px; padding: 4px; border: 1px solid #8b6914; text-align: center;">
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span>Temp:</span>
                                    <input type="text" value='""" + hp_temp + """' style="width: 60px; padding: 4px; border: 1px solid #8b6914; text-align: center;">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Combat Stats</h2>
                        <div style="text-align: center; padding: 15px;">
                            <div style="margin-bottom: 15px;">
                                <strong>Armor Class:</strong>
                                <div style="font-size: 1.8em; font-weight: bold; color: #8b6914;">""" + escape_html(str(ac_total)) + """</div>
                            </div>
                            <div style="margin-bottom: 15px;">
                                <strong>Initiative:</strong>
                                <div style="font-size: 1.5em; font-weight: bold; color: #8b6914;">""" + format_modifier(initiative) + """</div>
                            </div>
                            <div>
                                <strong>Speed:</strong>
                                <div style="font-size: 1.5em; font-weight: bold; color: #8b6914;">""" + escape_html(str(speed_total)) + """ ft</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>Features</h2>
                        <ul class="features-list">
"""
        
        for feature in features:
            html += f"""                            <li><strong>{escape_html(feature['name'])}</strong> (Lvl {escape_html(feature['level'])})</li>
"""
        
        if not features:
            html += """                            <li><em>No features</em></li>
"""
        
        html += """                        </ul>
                    </div>
                    
                    <div class="section">
                        <h2>Feats</h2>
                        <ul class="feats-list">
"""
        
        for feat in feats:
            html += f"""                            <li><strong>{escape_html(feat['name'])}</strong></li>
"""
        
        if not feats:
            html += """                            <li><em>No feats</em></li>
"""
        
        html += """                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="page">
            <div class="section">
                <h2>Equipment</h2>
                <ul class="inventory-list">
"""
        
        for item in inventory:
            count_text = f" x{item['count']}" if item['count'] != "1" else ""
            html += f"""                    <li>
                        <span>{escape_html(item['name'])}{escape_html(count_text)}</span>
                    </li>
"""
        
        if not inventory:
            html += """                    <li><em>No equipment</em></li>
"""
        
        html += """                </ul>
            </div>
            
            <div class="section">
                <h2>Wealth</h2>
                <div class="coins">
"""
        
        coin_order = ["PP", "GP", "EP", "SP", "CP"]
        for coin_type in coin_order:
            coin_value = coins.get(coin_type, "0")
            html += f"""                    <div class="coin-item">
                        <strong>{coin_type}</strong>
                        <input type="text" value="{escape_html(coin_value)}" />
                    </div>
"""
        
        html += """                </div>
            </div>
        </div>
        
        <div class="page">
"""
        
        if spell_slots:
            html += """            <div class="section">
                <h2>Spell Slots</h2>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
"""
            spell_levels = sorted(spell_slots.keys(), key=int)
            mid_point = (len(spell_levels) + 1) // 2
            
            html += """                    <div>
"""
            for level in spell_levels[:mid_point]:
                max_slots = int(spell_slots[level]["max"])
                used_slots = int(spell_slots[level].get("used", "0"))
                html += f"""                        <div class="spell-slot-level">
                            <strong>Level {level}:</strong>
                            <div class="spell-slot-bubbles">
"""
                for i in range(max_slots):
                    is_checked = i < used_slots
                    html += f"""                                <input type="checkbox" {'checked' if is_checked else ''}>
"""
                html += """                            </div>
                        </div>
"""
            html += """                    </div>
                    <div>
"""
            for level in spell_levels[mid_point:]:
                max_slots = int(spell_slots[level]["max"])
                used_slots = int(spell_slots[level].get("used", "0"))
                html += f"""                        <div class="spell-slot-level">
                            <strong>Level {level}:</strong>
                            <div class="spell-slot-bubbles">
"""
                for i in range(max_slots):
                    is_checked = i < used_slots
                    html += f"""                                <input type="checkbox" {'checked' if is_checked else ''}>
"""
                html += """                            </div>
                        </div>
"""
            html += """                    </div>
                </div>
            </div>
"""
        
        if spells:
            html += """            <div class="section">
                <h2>Spells</h2>
"""
            
            spells_by_level = {}
            for spell in spells:
                level = spell['level'] if spell['level'] and spell['level'] != '0' else 'Cantrip'
                if level not in spells_by_level:
                    spells_by_level[level] = []
                spells_by_level[level].append(spell)
            
            level_order = sorted(spells_by_level.keys(), key=lambda x: (x != 'Cantrip', int(x) if x.isdigit() else 0))
            
            for level in level_order:
                level_spells = spells_by_level[level]
                html += f"""                <div class="spell-level-toggle" onclick="toggleSpell(this)">
                    <h3>Level {escape_html(str(level))} ({len(level_spells)} spells)</h3>
                    <span>▼</span>
                </div>
                <div class="spell-level-content">
"""
                for spell in level_spells:
                    prepared_mark = "●" if spell['prepared'] and spell['prepared'] != "0" else "○"
                    html += f"""                    <div style="background: #f5f1e8; padding: 8px; border-radius: 3px; border-left: 3px solid #8b6914; margin-bottom: 8px;">
                        <div><strong>{prepared_mark} {escape_html(spell['name'])}</strong></div>
"""
                    if spell['school']:
                        html += f"""                        <div style="font-size: 0.85em;"><strong>School:</strong> {escape_html(spell['school'])}</div>
"""
                    if spell['description']:
                        html += f"""                        <div class="spell-description">{spell['description']}</div>
"""
                    html += """                    </div>
"""
                html += """                </div>
"""
            
            html += """                <script>
                function toggleSpell(elem) {
                    const content = elem.nextElementSibling;
                    content.classList.toggle('active');
                }
                </script>
            </div>
"""
        
        html += """        </div>
    </div>
</body>
</html>"""
        
        return html, None
    
    except Exception as e:
        return None, str(e)


# Web routes
@app.route('/')
def index():
    """Home page with upload form."""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FGU Character Sheet Generator</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Book Antiqua', 'Palatino Linotype', Palatino, serif;
                background: linear-gradient(135deg, #f5f1e8 0%, #e8ddd4 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border: 3px solid #8b6914;
                border-radius: 8px;
                padding: 40px;
                max-width: 600px;
                width: 100%;
                box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            }
            h1 {
                color: #8b6914;
                text-align: center;
                margin-bottom: 10px;
                font-size: 2em;
            }
            .subtitle {
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 0.95em;
            }
            .upload-area {
                border: 2px dashed #8b6914;
                border-radius: 6px;
                padding: 40px 20px;
                text-align: center;
                margin-bottom: 20px;
                cursor: pointer;
                transition: background 0.3s;
            }
            .upload-area:hover {
                background: #f5f1e8;
            }
            .upload-area.dragover {
                background: #f5f1e8;
                border-color: #6b5310;
            }
            .upload-icon {
                font-size: 3em;
                margin-bottom: 10px;
            }
            input[type="file"] {
                display: none;
            }
            button {
                background: #8b6914;
                color: white;
                border: none;
                padding: 12px 30px;
                font-size: 1em;
                border-radius: 4px;
                cursor: pointer;
                width: 100%;
                font-weight: bold;
                transition: background 0.3s;
            }
            button:hover {
                background: #6b5310;
            }
            #fileName {
                margin-top: 10px;
                color: #666;
                font-size: 0.9em;
            }
            .info {
                background: #f5f1e8;
                border-left: 4px solid #8b6914;
                padding: 15px;
                margin-top: 20px;
                border-radius: 4px;
                font-size: 0.9em;
                line-height: 1.6;
            }
            .info h3 {
                color: #8b6914;
                margin-bottom: 10px;
            }
            .info ul {
                margin-left: 20px;
            }
            .error {
                color: #c12727;
                background: #ffe6e6;
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 20px;
                display: none;
            }
            @media (max-width: 600px) {
                .container {
                    padding: 20px;
                }
                h1 {
                    font-size: 1.5em;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>FGU Character Sheet Generator</h1>
            <p class="subtitle">Convert Fantasy Grounds Unity XML to HTML</p>
            
            <div class="error" id="error"></div>
            
            <form id="uploadForm" enctype="multipart/form-data">
                <div class="upload-area" id="uploadArea">
                    <div class="upload-icon">📁</div>
                    <p><strong>Click to upload or drag & drop</strong></p>
                    <p style="font-size: 0.9em; color: #666; margin-top: 5px;">XML character file (max 16MB)</p>
                    <input type="file" id="fileInput" name="file" accept=".xml" required>
                </div>
                <div id="fileName"></div>
                <button type="submit">Generate Character Sheet</button>
            </form>
            
            <div class="info">
                <h3>How to use:</h3>
                <ul>
                    <li>Export your character from Fantasy Grounds Unity as XML</li>
                    <li>Upload the XML file here</li>
                    <li>Get a beautiful HTML character sheet</li>
                    <li>Print or save as PDF</li>
                </ul>
            </div>
        </div>
        
        <script>
            const uploadArea = document.getElementById('uploadArea');
            const fileInput = document.getElementById('fileInput');
            const fileName = document.getElementById('fileName');
            const form = document.getElementById('uploadForm');
            const errorDiv = document.getElementById('error');
            
            uploadArea.addEventListener('click', () => fileInput.click());
            
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                fileInput.files = e.dataTransfer.files;
                updateFileName();
            });
            
            fileInput.addEventListener('change', updateFileName);
            
            function updateFileName() {
                if (fileInput.files.length > 0) {
                    fileName.textContent = '✓ ' + fileInput.files[0].name;
                    fileName.style.color = '#2d7a2d';
                } else {
                    fileName.textContent = '';
                }
            }
            
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                errorDiv.style.display = 'none';
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                const button = form.querySelector('button');
                button.disabled = true;
                button.textContent = 'Generating...';
                
                try {
                    const response = await fetch('/generate', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.error || 'Unknown error');
                    }
                    
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'character_sheet.html';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                } catch (error) {
                    errorDiv.textContent = 'Error: ' + error.message;
                    errorDiv.style.display = 'block';
                } finally {
                    button.disabled = false;
                    button.textContent = 'Generate Character Sheet';
                }
            });
        </script>
    </body>
    </html>
    '''


@app.route('/generate', methods=['POST'])
def generate():
    """Generate character sheet from uploaded XML."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.xml'):
        return jsonify({'error': 'File must be XML format'}), 400
    
    try:
        xml_content = file.read()
        html, error = parse_fgu_character_to_html(xml_content)
        
        if error:
            return jsonify({'error': error}), 400
        
        # Extract character name for filename
        filename = "character_sheet.html"
        try:
            root = ET.fromstring(xml_content)
            char = root.find("character")
            if char is not None:
                name_elem = char.find("name")
                if name_elem is not None and name_elem.text:
                    char_name = name_elem.text.strip()
                    if char_name:
                        # Clean filename - remove invalid characters
                        clean_name = "".join(c for c in char_name if c.isalnum() or c in (' ', '_', '-')).strip()
                        if clean_name:
                            filename = f"{clean_name}.html"
        except:
            pass
        
        # Return HTML as downloadable file
        return send_file(
            BytesIO(html.encode('utf-8')),
            mimetype='text/html',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check for Vercel."""
    return jsonify({'status': 'ok'}), 200


# Vercel requires this for deployment
app.wsgi_app = app.wsgi_app


if __name__ == '__main__':
    # Local development
    app.run(debug=True, host='0.0.0.0', port=5000)
