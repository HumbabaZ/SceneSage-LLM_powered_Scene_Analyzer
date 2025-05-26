# SceneSage - LLM-powered Scene Analyzer

A command-line tool that processes subtitle files (.srt) and uses Large Language Models to generate structured scene annotations.

## Overview

SceneSage analyzes movie scenes by:

- Automatically segmenting subtitles into scenes based on timing gaps (≥4 seconds)
- Extracting structured information using Google Gemini API:
  - One-sentence scene summaries
  - Character identification
  - Mood/emotion analysis
  - Cultural references

## Technical Implementation

- **LLM Integration**: Google Gemini 2.0 Flash for natural language processing
- **Context Caching**: Explicit caching of movie background information to reduce API costs
- **Scene Detection**: Automatic segmentation based on subtitle timing analysis
- **Context Enhancement**: Wikipedia content integration for improved analysis accuracy

## Setup

### Prerequisites

- Python 3.7+
- Google Gemini API key

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure API key:
   ```bash
   cp .env
   # Edit .env and set GEMINI_API_KEY=your_api_key
   ```

3. Obtain API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Optional: Load Movie Context

For enhanced analysis, extract Wikipedia content:
```bash
python extract_wiki_sections.py
```

## Usage

### Basic Analysis

```bash
python ai_film_project.py input.srt --output results.json
```

### Options

```bash
python ai_film_project.py input.srt [options]

Options:
  --model MODEL         Specify Gemini model (default: gemini-2.0-flash)
  --output FILE         Output JSON file path
```

### Cache Management

The tool automatically manages context caching:
- Creates cache on first run
- Stores cache reference in .env file
- Reuses cache for subsequent requests
- Handles cache expiration automatically

## Output Format

```json
[
  {
    "start": "00:00:22,719",
    "end": "00:00:31,507", 
    "transcript": "Scene dialogue text",
    "summary": "Brief scene description",
    "characters": ["Character1", "Character2"],
    "mood": "emotional tone",
    "cultural_refs": ["reference1", "reference2"]
  }
]
```

## Requirements

google-genai>=0.8.0
python-dotenv>=1.0.0
requests>=2.31.0 