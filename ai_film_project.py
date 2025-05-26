import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
import requests  # For API calls
from google import genai
from google.genai import types

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, skip

#Load movie context from Wikipedia section files
def load_movie_context(sections_dir="plan9_sections"):    
    context_parts = []
    
    # Define the order of sections for better organization
    section_order = [
        "Introduction.txt",
        "Plot.txt",
        "Cast.txt", 
        "Production.txt",
        "Reception.txt",
        "Legacy.txt",
        "Documentaries.txt",
    ]
    
    for section_file in section_order:
        file_path = os.path.join(sections_dir, section_file)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        section_name = section_file.replace('.txt', '').replace('_', ' ')
                        context_parts.append(f"=== {section_name.upper()} ===\n{content}")
            except Exception as e:
                print(f"Warning: Could not read {section_file}: {e}")
    
    return "\n\n".join(context_parts)

# Load comprehensive movie context
system_instruction = load_movie_context()

# Fallback basic info if files not available
if not system_instruction:
    movie_intro = "This movie, Plan 9 from Outer Space, is a 1957 American independent science fiction-horror film. The film's storyline concerns extraterrestrials who seek to stop humanity from creating a doomsday weapon that could destroy the universe.[8] The aliens implement 'Plan 9', a scheme to resurrect the Earth's dead. By causing chaos, the aliens hope the crisis will force humanity to listen to them; otherwise, the aliens will destroy mankind with armies of the undead."
    influence_intro="and his film were posthumously given two Golden Turkey Awards for Worst Director Ever and Worst Film Ever. It has since been called 'the epitome of so-bad-it's-good cinema'[10] and gained a large cult following."
    main_character_intro = "Pilot Jeff Trent, Wife Paula Trent, Lieutenant John Harper, Colonel Tom Edwards, The narrator, Patrolman Larry, Patrolman Kelton, Inspector Daniel Clay, and the alien invaders."
    system_instruction = f"{movie_intro}\ninfluence_intro\n{main_character_intro}"

def parse_srt(file_path):
    """Parse an SRT file into a list of subtitle entries."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Split by blank lines to get subtitle blocks
    subtitle_blocks = content.strip().split('\n\n')
    subtitles = []
    
    for block in subtitle_blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # Extract timestamp line
        timestamp_line = lines[1]
        times = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3})', timestamp_line)
        if len(times) != 2:
            continue
        
        start_time, end_time = times
        
        # Join all text lines
        text = ' '.join(lines[2:])
        
        subtitles.append({
            'index': int(lines[0]),
            'start': start_time,
            'end': end_time,
            'text': text
        })
    
    return subtitles

def group_into_scenes(subtitles, min_pause_seconds=4):
    """Group subtitles into scenes based on pauses."""
    scenes = []
    current_scene = []
    
    for i, subtitle in enumerate(subtitles):
        if not current_scene:
            current_scene.append(subtitle)
            continue
            
        # Check if there's a significant pause after the previous subtitle
        prev_end = datetime.strptime(subtitles[i-1]['end'], '%H:%M:%S,%f')
        current_start = datetime.strptime(subtitle['start'], '%H:%M:%S,%f')
        
        pause_duration = (current_start - prev_end).total_seconds()
        
        if pause_duration >= min_pause_seconds:
            # End current scene
            if current_scene:
                scenes.append(current_scene)
                current_scene = []
        
        current_scene.append(subtitle)
    
    # Add the last scene
    if current_scene:
        scenes.append(current_scene)
    
    return scenes

def analyze_scene_with_llm(scene_text, model):
    if model.startswith("gemini"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        model_name = model  # 例如 "gemini-2.0-flash"
        prompt = f"""
        Analyze this movie scene transcription:

        "{scene_text}"

        Provide a structured analysis with:
        1. A one-sentence summary
        2. Characters in the scene (list)
        3. Overall mood/emotion, up to 3 words
        4. Up to 3 cultural references (list, can be empty)

        Please format your response as follows:
        Summary: [your one-sentence summary]
        Characters: [character1, character2, ...]
        Mood: [mood/emotion]
        Cultural References: [reference1, reference2, reference3] (or [] if none)
        """
        client = genai.Client(api_key=api_key)

        cache = client.caches.create(
            model=model_name,
            config=types.CreateCachedContentConfig(
                system_instruction=system_instruction,
            )
        )        
        cache_name = cache.name        
        #print("the cache is saved as: cache_name:", cache_name)

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt],
            config=types.GenerateContentConfig(
                cached_content=cache_name
            )
        )
        return parse_llm_response(response.text)
    else:
        raise ValueError(f"Unsupported model: {model}")

def parse_llm_response(response_text):
    """Parse the LLM response text into structured data."""
    try:
        # Initialize default values
        analysis = {
            "summary": "",
            "characters": [],
            "mood": "",
            "cultural_refs": []
        }
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Summary:"):
                analysis["summary"] = line.replace("Summary:", "").strip()
            elif line.startswith("Characters:"):
                chars_text = line.replace("Characters:", "").strip()
                # Parse list format [item1, item2, ...] or comma-separated
                if chars_text.startswith('[') and chars_text.endswith(']'):
                    chars_text = chars_text[1:-1]
                if chars_text:
                    analysis["characters"] = [char.strip() for char in chars_text.split(',') if char.strip()]
            elif line.startswith("Mood:"):
                analysis["mood"] = line.replace("Mood:", "").strip()
            elif line.startswith("Cultural References:"):
                refs_text = line.replace("Cultural References:", "").strip()
                # Parse list format [item1, item2, ...] or comma-separated
                if refs_text.startswith('[') and refs_text.endswith(']'):
                    refs_text = refs_text[1:-1]
                if refs_text and refs_text != "[]":
                    analysis["cultural_refs"] = [ref.strip() for ref in refs_text.split(',') if ref.strip()]
        
        return analysis
        
    except Exception as e:
        # Fallback: return basic analysis if parsing fails
        return {
            "summary": "Analysis parsing failed",
            "characters": [],
            "mood": "unknown",
            "cultural_refs": []
        }

def main():
    parser = argparse.ArgumentParser(description="LLM-powered scene analyzer for subtitle files")
    parser.add_argument("srt_file", help="Path to the .srt subtitle file")
    parser.add_argument("--model", default="gemini-2.0-flash", help="LLM model to use (e.g., openai:gpt-4o)")
    parser.add_argument("--output", default="output.json", help="Output JSON file path")
    args = parser.parse_args()
    
    # Parse SRT file
    subtitles = parse_srt(args.srt_file)
    
    # Group into scenes
    scenes = group_into_scenes(subtitles)
    
    # Analyze each scene
    results = []
    for scene in scenes:
        scene_text = " ".join(sub["text"] for sub in scene)
        scene_start = scene[0]["start"]
        scene_end = scene[-1]["end"]
        
        analysis = analyze_scene_with_llm(scene_text, args.model)
        
        results.append({
            "start": scene_start,
            "end": scene_end,
            "transcript": scene_text,
            "summary": analysis["summary"],
            "characters": analysis["characters"],
            "mood": analysis["mood"],
            "cultural_refs": analysis["cultural_refs"]
        })
    
    # Output results
    output_json = json.dumps(results, indent=2)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
    else:
        print(output_json)

if __name__ == "__main__":
    main()