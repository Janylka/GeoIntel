import json
import os
from google import genai
from geointel.db.session import get_db

async def generate_explanation(scope: str, subject_id: int, decade: str, lang: str, metrics_data: dict) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = f"""
    You are an expert agricultural AI assistant for GeoIntel in Kyrgyzstan.
    Analyze the drought metrics and yield forecast provided in JSON for {scope} ID {subject_id} on decade {decade}.
    
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