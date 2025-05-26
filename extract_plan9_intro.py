import requests
from bs4 import BeautifulSoup
import re
import os

# Wikipedia page URL
URL = "https://en.wikipedia.org/wiki/Plan_9_from_Outer_Space"

def clean_filename(title):
    # Keep only alphanumeric characters and underscores
    return re.sub(r'[^a-zA-Z0-9_]', '_', title)

def extract_text_content(element):
    """Extract clean text from an element, removing citations and edit links"""
    if not element:
        return ""
    
    # Remove citation elements like [1], [2], etc.
    for cite in element.find_all(['sup', 'span'], class_=['reference', 'mw-editsection']):
        cite.decompose()
    
    return element.get_text(separator=" ", strip=True)

def main():
    print("Fetching Wikipedia page...")
    
    # Add headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    resp = requests.get(URL, headers=headers)
    resp.raise_for_status()
    print(f"Page fetched successfully, status code: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, "html.parser")

    # Find main content area
    content_div = soup.find("div", {"class": "mw-parser-output"})
    if not content_div:
        print("ERROR: Main content area not found")
        return
    
    print("SUCCESS: Main content area found")
    
    # Find all heading divs with the new structure
    heading_divs = content_div.find_all("div", {"class": "mw-heading"})
    print(f"Found {len(heading_divs)} heading divs")
    
    # Also try to find direct h2 elements as backup
    direct_h2s = content_div.find_all("h2")
    print(f"Found {len(direct_h2s)} direct h2 elements")
    
    sections = []
    
    # Method 1: Use the new mw-heading structure
    if heading_divs:
        print("\nUsing mw-heading structure...")
        
        for i, heading_div in enumerate(heading_divs):
            # Get the h2 element inside the div
            h2_element = heading_div.find("h2")
            if not h2_element:
                continue
            
            section_title = h2_element.get_text().strip()
            print(f"Processing section {i+1}: {section_title}")
            
            # Find content after this heading div until the next heading div
            content_elements = []
            current_element = heading_div.next_sibling
            
            while current_element:
                # Stop when we hit the next heading div
                if (hasattr(current_element, 'get') and 
                    current_element.get('class') and 
                    'mw-heading' in current_element.get('class', [])):
                    break
                
                # Collect content elements
                if hasattr(current_element, 'name'):
                    if current_element.name in ['p', 'ul', 'ol', 'dl', 'table']:
                        content_elements.append(current_element)
                    elif current_element.name == 'div':
                        # Look for content inside divs
                        inner_content = current_element.find_all(['p', 'ul', 'ol', 'dl'])
                        content_elements.extend(inner_content)
                
                current_element = current_element.next_sibling
            
            # Extract text from collected elements
            section_content = []
            for elem in content_elements:
                text = extract_text_content(elem)
                if text and len(text.strip()) > 20:
                    section_content.append(text)
            
            if section_content:
                content_text = "\n\n".join(section_content)
                sections.append((section_title, content_text))
                print(f"  SUCCESS: Extracted {len(section_content)} paragraphs, {len(content_text)} characters")
            else:
                print(f"  WARNING: No substantial content found for {section_title}")
    
    # Method 2: Fallback to direct h2 elements
    elif direct_h2s:
        print("\nFallback: Using direct h2 elements...")
        
        for i, h2 in enumerate(direct_h2s):
            section_title = h2.get_text().strip()
            print(f"Processing section {i+1}: {section_title}")
            
            # Find content after this h2
            content_elements = []
            current_element = h2.next_sibling
            
            while current_element:
                if current_element.name == 'h2':
                    break
                
                if hasattr(current_element, 'name') and current_element.name in ['p', 'ul', 'ol', 'dl']:
                    content_elements.append(current_element)
                
                current_element = current_element.next_sibling
            
            # Extract text
            section_content = []
            for elem in content_elements:
                text = extract_text_content(elem)
                if text and len(text.strip()) > 20:
                    section_content.append(text)
            
            if section_content:
                content_text = "\n\n".join(section_content)
                sections.append((section_title, content_text))
                print(f"  SUCCESS: Extracted {len(section_content)} paragraphs, {len(content_text)} characters")

    print(f"\nTotal sections extracted: {len(sections)}")
    
    # If still no sections, extract introduction
    if not sections:
        print("No sections found. Extracting introduction...")
        intro_content = []
        
        for elem in content_div.find_all('p'):
            text = extract_text_content(elem)
            if text and len(text.strip()) > 20:
                intro_content.append(text)
        
        if intro_content:
            intro_text = "\n\n".join(intro_content)
            sections.append(("Introduction", intro_text))
            print(f"Extracted introduction section ({len(intro_text)} characters)")
    
    # Output to files
    out_dir = "plan9_sections"
    os.makedirs(out_dir, exist_ok=True)
    
    # Clear existing files
    for filename in os.listdir(out_dir):
        if filename.startswith("plan9_") and filename.endswith(".txt"):
            os.remove(os.path.join(out_dir, filename))
    
    for title, content in sections:
        filename = f"{clean_filename(title)}.txt"
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{content}\n")
        
        print(f"SAVED: {filename} ({len(content)} characters)")

    print(f"\nCOMPLETE! {len(sections)} files saved in {out_dir}/ directory")
    
    # List all created files
    if os.path.exists(out_dir):
        files = [f for f in os.listdir(out_dir) if f.startswith("plan9_")]
        print(f"Created files:")
        for file in sorted(files):
            print(f"  - {file}")

if __name__ == "__main__":
    main()
