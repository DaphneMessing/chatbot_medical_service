
from bs4 import BeautifulSoup
import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Any


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


# Map HMO column index to HMO name
HMO_MAPPING: Dict[int, str] = {
    1: "מכבי",
    2: "מאוחדת",
    3: "כללית"
}

# Map Hebrew tier names to normalized format
TIERS: List[str] = ["זהב", "כסף", "ארד"]

def parse_html_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def load_all_html_files(directory: str) -> Dict[str, str]:
    knowledge_base: Dict[str, str] = {}
    for file in os.listdir(directory):
        if file.endswith('.html'):
            file_path = os.path.join(directory, file)
            key = os.path.splitext(file)[0]
            knowledge_base[key] = parse_html_file(file_path)
            logging.info(f"Loaded file: {file}")
    return knowledge_base

def extract_chunks_from_html(html_files: Dict[str, str], file_mappings: List[tuple]) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    for filename, category in file_mappings:
        html_content = html_files.get(filename, "")
        if not html_content:
            logging.warning(f"No content found for file: {filename}")
            continue

        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract intro paragraphs and service descriptions before the table
        intro_parts = []
        service_descriptions = []
        reached_table = False

        for tag in soup.find_all(['p', 'ul', 'table']):
            if tag.name == 'table':
                reached_table = True
                break
            elif tag.name == 'p':
                intro_parts.append(tag.get_text(strip=True))
            elif tag.name == 'ul':
                items = tag.find_all('li')
                for item in items:
                    text = item.get_text(strip=True)
                    if ':' in text:
                        name, desc = text.split(':', 1)
                        service_descriptions.append({"service": name.strip(), "description": desc.strip()})
                    else:
                        intro_parts.append(text)

        if intro_parts:
            chunks.append({
                "category": category,
                "section": "מבוא",
                "text": "\n".join(intro_parts)
            })

        for desc in service_descriptions:
            chunks.append({
                "category": category,
                "section": "פירוט שירות",
                "service": desc["service"],
                "text": f"הסבר על השירות {desc['service']} בקטגוריה {category}: {desc['description']}"
            })

        table = soup.find('table')
        if not table:
            logging.warning(f"No table found in file: {filename}")
            continue

        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols:
                continue  # Skip header row

            service_name = cols[0].get_text(strip=True)

            for hmo_idx, hmo_name in HMO_MAPPING.items():
                hmo_info = cols[hmo_idx]
                parts = hmo_info.decode_contents().split('<br>')

                for part in parts:
                    part_soup = BeautifulSoup(part, 'html.parser')
                    text = part_soup.get_text(strip=True)
                    for tier in TIERS:
                        if text.startswith(tier):
                            benefit_text = text.replace(tier + ":", "").strip()
                            chunk = {
                                "category": category,
                                "service": service_name,
                                "hmo": hmo_name,
                                "tier": tier,
                                "text": f"בשירות {service_name} בקטגוריה {category}, עבור חברי {hmo_name} במסלול {tier}: {benefit_text}"
                            }
                            chunks.append(chunk)
        logging.info(f"Extracted chunks from: {filename}")

    return chunks


def get_chunks_for_embedding() -> List[Dict[str, Any]]:
    BASE_DIR = Path(__file__).resolve().parent.parent
    html_dir = BASE_DIR / "data" / "phase2_data"
    html_files = load_all_html_files(str(html_dir))

    FILES = [
        ("alternative_services", "רפואה משלימה"),
        ("communication_clinic_services", "מרפאות תקשורת"),
        ("dental_services", "מרפאות שיניים"),
        ("optometry_services", "אופטומטריה"),
        ("pragrency_services", "הריון"),
        ("workshops_services", "סדנאות בריאות")
    ]
    return extract_chunks_from_html(html_files, FILES)

def run_extraction():
    BASE_DIR = Path(__file__).resolve().parent.parent
    output_path = BASE_DIR / "data" / "structured_kb.json"
    chunks = get_chunks_for_embedding()

    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    logging.info(f"✅ Extracted {len(chunks)} chunks and saved to {output_path}.")

if __name__ == "__main__":
    run_extraction()
