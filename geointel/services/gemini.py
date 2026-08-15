import json
import os
from google import genai

async def generate_explanation(
    scope: str, 
    subject_id: int, 
    decade: str, 
    lang: str, 
    metrics_data: dict
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Gemini API key is not configured."

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an expert agricultural AI assistant for GeoIntel in Kyrgyzstan.
    Analyze the drought metrics provided in JSON for {scope} ID {subject_id} on decade {decade}.
    
    CRITICAL RULE: Do NOT invent or state any numbers, metrics, or statistics that are NOT present in the input JSON below.
    
    Input JSON:
    {json.dumps(metrics_data, ensure_ascii=False)}
    
    Provide a concise, practical analysis and recommendations for the farmer in language: {lang}.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    
    return response.text