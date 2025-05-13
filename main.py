from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import os
import shutil
from extract_text import extract_text_from_pdf
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import BackgroundTasks
import tiktoken
import json
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
import re
import uvicorn

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client with API key from environment variables
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def count_tokens(prompt: str, model: str = "gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(prompt))

# FastAPI app
app = FastAPI()

app.mount("/main", StaticFiles(directory="main", html=True), name="main")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def build_ranked_results(cv_results):
    for res in cv_results:
        score = int(res.get("score", 0))
        if score >= 80:
            res["match_level"] = "Strong Match"
        elif score >= 60:
            res["match_level"] = "Moderate Match"
        else:
            res["match_level"] = "Weak Match"
    return sorted(cv_results, key=lambda x: int(x.get("score", 0)), reverse=True)

def analyze_cv(jd_text, cv_text, filename):
    prompt = f"""
You are an HR assistant helping evaluate a candidate's CV against a job description.

Analyze the following CV in comparison to the job description. Provide a score from 0 to 100 for how well it matches, along with:

- A match level: "High", "Medium", or "Low"
- Bullet-point **strengths**
- Bullet-point **weaknesses**

Use this output format (JSON):

{{
  "score": <int>, 
  "match_level": "<High|Medium|Low>", 
  "strength": ["<bullet 1>", "<bullet 2>", ...], 
  "weakness": ["<bullet 1>", "<bullet 2>", ...]
}}

### Job Description:
{jd_text}

### Candidate CV:
{cv_text}
"""
    print("Token count:", count_tokens(prompt))
    # Check if the token count exceeds the limit
    if count_tokens(prompt) > 4096:
        return {"error": "Prompt exceeds token limit."}
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are an expert HR assistant that returns only structured JSON analysis based on job description and CV comparison."},
            {"role": "user", "content": prompt}],
        temperature=0.4
    )
    content = response.choices[0].message.content
    # Clean up the response
    content = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", content).strip()
    try:
        # Attempt to parse the JSON response
        data = json.loads(content)
    except json.JSONDecodeError:
        # If parsing fails, return an error message
        return {"error": "Failed to parse response from OpenAI."}
    # data = json.loads(content)
    data["filename"] = filename
    return data

@app.post("/upload")
async def upload_files(jd: UploadFile = File(...), cvs: List[UploadFile] = File(...)):
    jd_path = os.path.join(UPLOAD_DIR, f"jd_{jd.filename}")
    with open(jd_path, "wb") as f:
        shutil.copyfileobj(jd.file, f)

    jd_text = extract_text_from_pdf(jd_path)

    results = []
    for cv in cvs:
        cv_path = os.path.join(UPLOAD_DIR, f"cv_{cv.filename}")
        with open(cv_path, "wb") as f:
            shutil.copyfileobj(cv.file, f)

        cv_text = extract_text_from_pdf(cv_path)
        result = analyze_cv(jd_text, cv_text, cv.filename)
        results.append(result)

    ranked = build_ranked_results(results)
    print("Ranked results:", ranked)
    return JSONResponse(content={"results": ranked})

@app.post("/download-excel")
async def download_excel(results: List[Dict]):
    """Generate and return an Excel file from the analysis results."""
    if not results:
        return JSONResponse(status_code=400, content={"error": "No results provided"})
    
    # Create a workbook and select the active worksheet
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "CV Analysis"
    
    # Add headers
    headers = ["Rank", "Filename", "Score", "Match Level", "Strengths", "Weaknesses"]
    worksheet.append(headers)
    
    # Style headers
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
    
    # Add data rows
    for i, result in enumerate(results, 1):
        strengths_text = "\n".join([f"• {s}" for s in result.get("strength", [])])
        weaknesses_text = "\n".join([f"• {w}" for w in result.get("weakness", [])])
        
        row = [
            i,  # Rank
            result.get("filename", ""),
            result.get("score", 0),
            result.get("match_level", ""),
            strengths_text,
            weaknesses_text
        ]
        worksheet.append(row)
    
    # Adjust column widths
    for col in worksheet.columns:
        max_length = 0
        column = col[0].column_letter
        
        for cell in col:
            if cell.value:
                cell_length = len(str(cell.value).split('\n')[0])
                if cell_length > max_length:
                    max_length = cell_length
            
            # Set text wrapping for strengths and weaknesses columns
            if column in ['E', 'F']:  # Columns E and F are strengths and weaknesses
                cell.alignment = Alignment(wrapText=True, vertical='top')
        
        # Set column width with some padding
        adjusted_width = max_length + 4
        worksheet.column_dimensions[column].width = min(adjusted_width, 50)
    
    # Save to a BytesIO object
    excel_file = BytesIO()
    workbook.save(excel_file)
    excel_file.seek(0)
    
    # Return the Excel file as a streaming response
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=cv_analysis_report.xlsx"}
    )
