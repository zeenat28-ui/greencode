import os
from PIL import Image, ImageDraw, ImageFont

def generate_devpost_thumbnail(output_path="assets/thumbnail.png"):
    width, height = 1280, 720
    im = Image.new("RGB", (width, height), (11, 17, 30))  # Deep enterprise navy #0B111E
    draw = ImageDraw.Draw(im)

    # Grid background lines
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill=(20, 30, 48), width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill=(20, 30, 48), width=1)

    # Fonts
    font_hero = ImageFont.truetype("arialbd.ttf", 54)
    font_sub = ImageFont.truetype("arial.ttf", 22)
    font_meta = ImageFont.truetype("arial.ttf", 16)
    font_bold = ImageFont.truetype("arialbd.ttf", 16)
    font_num = ImageFont.truetype("arialbd.ttf", 64)
    font_code = ImageFont.truetype("consola.ttf", 14) if os.path.exists("C:\\Windows\\Fonts\\consola.ttf") else ImageFont.truetype("arial.ttf", 14)

    # Top Tag
    draw.rounded_rectangle([60, 50, 410, 84], radius=6, fill=(16, 36, 40), outline=(5, 150, 105), width=1)
    draw.text((75, 58), "AMAZON DEVELOPER HACKATHON 2026", fill=(52, 211, 153), font=font_bold)

    # Hero Title
    draw.text((60, 104), "GreenCode", fill=(255, 255, 255), font=font_hero)
    draw.ellipse([345, 126, 360, 141], fill=(52, 211, 153))

    # Enterprise Tagline
    draw.text((60, 178), "Enterprise Green Software & Operational Carbon Auditor", fill=(203, 213, 225), font=font_sub)
    draw.text((60, 215), "Automated AST Remediation & SCI Quality Gates via Amazon Bedrock & Alexa+ Voice MCP", fill=(148, 163, 184), font=font_meta)

    # 3 Pill Badges
    pills = [
        ("AWS Bedrock GenAI", (15, 35, 60), (56, 189, 248), (30, 60, 100)),
        ("Alexa+ Voice MCP", (35, 20, 60), (192, 132, 252), (70, 40, 110)),
        ("ISO/IEC 21031 (GSF SCI)", (15, 45, 35), (52, 211, 153), (30, 80, 60)),
    ]
    px = 60
    py = 260
    for title, bg, fg, border in pills:
        pw = len(title) * 10 + 24
        draw.rounded_rectangle([px, py, px + pw, py + 34], radius=6, fill=bg, outline=border, width=1)
        draw.text((px + 12, py + 8), title, fill=fg, font=font_bold)
        px += pw + 14

    # Bottom Area: Left Card (Quality Gate), Right Card (Code Diff)
    # Left Card
    c1_x, c1_y, c1_w, c1_h = 60, 325, 350, 345
    draw.rounded_rectangle([c1_x, c1_y, c1_x + c1_w, c1_y + c1_h], radius=10, fill=(18, 26, 43), outline=(35, 49, 77), width=1)
    draw.text((c1_x + 20, c1_y + 18), "CI/CD QUALITY GATE", fill=(148, 163, 184), font=font_bold)

    draw.rounded_rectangle([c1_x + 20, c1_y + 48, c1_x + 190, c1_y + 78], radius=5, fill=(10, 40, 30), outline=(16, 185, 129), width=1)
    draw.text((c1_x + 32, c1_y + 54), "COMPLIANT (>= 75)", fill=(52, 211, 153), font=font_bold)

    draw.text((c1_x + 20, c1_y + 95), "92", fill=(52, 211, 153), font=font_num)
    draw.text((c1_x + 110, c1_y + 122), "/ 100 Grade A", fill=(148, 163, 184), font=font_sub)

    draw.line([(c1_x + 20, c1_y + 180), (c1_x + c1_w - 20, c1_y + 180)], fill=(35, 49, 77), width=1)
    draw.text((c1_x + 20, c1_y + 198), "Energy Reduction: -63.4% Joules", fill=(241, 245, 249), font=font_bold)
    draw.text((c1_x + 20, c1_y + 230), "Carbon Intensity: 0.19 gCO2e / run", fill=(148, 163, 184), font=font_meta)
    draw.text((c1_x + 20, c1_y + 260), "Regional Grid: AWS us-east-1 Live", fill=(56, 189, 248), font=font_meta)
    draw.text((c1_x + 20, c1_y + 290), "Tamper-Proof SHA-256 Ledger: VERIFIED", fill=(52, 211, 153), font=font_code)

    # Right Card: Bedrock Eco-Refactoring Diff
    c2_x, c2_y, c2_w, c2_h = 435, 325, 785, 345
    draw.rounded_rectangle([c2_x, c2_y, c2_x + c2_w, c2_y + c2_h], radius=10, fill=(18, 26, 43), outline=(35, 49, 77), width=1)
    draw.text((c2_x + 20, c2_y + 18), "AMAZON BEDROCK CONVERSE -- BEHAVIOURAL-PRESERVING ECO REFACTOR", fill=(148, 163, 184), font=font_bold)

    diff_y = c2_y + 50
    diff_h = 270

    # Before Box (Red)
    draw.rounded_rectangle([c2_x + 20, diff_y, c2_x + 380, diff_y + diff_h], radius=8, fill=(28, 16, 22), outline=(90, 25, 35), width=1)
    draw.text((c2_x + 35, diff_y + 12), "BEFORE: O(N^2) Quadratic Search", fill=(248, 113, 113), font=font_bold)
    code_before = [
        "result = []",
        "for item in raw_stream:",
        "    if item in cache:       # O(N) linear",
        "        result.append(item) # High alloc",
        "",
        "# Energy Demand : 84.2 Joules",
        "# Operational CO2: 8.9 gCO2e",
        "# Verdict       : BLOCKED (Quality Gate)",
    ]
    for i, line in enumerate(code_before):
        color = (248, 113, 113) if "#" in line else (203, 213, 225)
        draw.text((c2_x + 35, diff_y + 45 + (i * 24)), line, fill=color, font=font_code)

    # After Box (Green)
    draw.rounded_rectangle([c2_x + 405, diff_y, c2_x + 765, diff_y + diff_h], radius=8, fill=(12, 32, 28), outline=(15, 80, 60), width=1)
    draw.text((c2_x + 420, diff_y + 12), "AFTER: Bedrock Refactored O(N)", fill=(52, 211, 153), font=font_bold)
    code_after = [
        "cache_set = set(cache)      # O(1) hash set",
        "result = [",
        "    x for x in raw_stream   # Gen comp",
        "    if x in cache_set",
        "]",
        "# Energy Demand : 18.6 Joules (-78%)",
        "# Operational CO2: 1.9 gCO2e (-78%)",
        "# Verdict       : PASSED & VERIFIED",
    ]
    for i, line in enumerate(code_after):
        color = (52, 211, 153) if "#" in line else (203, 213, 225)
        draw.text((c2_x + 420, diff_y + 45 + (i * 24)), line, fill=color, font=font_code)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    im.save(output_path, "PNG")
    print(f"Successfully generated thumbnail at {output_path}")

if __name__ == "__main__":
    generate_devpost_thumbnail()

