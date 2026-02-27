from pathlib import Path
from typing import Optional
import re


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        raise RuntimeError(f"PDF解析失败: {e}")


def extract_text_from_docx(docx_path: Path) -> str:
    try:
        from docx import Document
        doc = Document(docx_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        raise RuntimeError(f"DOCX解析失败: {e}")


def parse_resume(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"简历文件不存在: {file_path}")
    
    ext = path.suffix.lower()
    if ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext in [".docx", ".doc"]:
        text = extract_text_from_docx(path)
    else:
        raise ValueError(f"不支持的简历格式: {ext}")
    
    return parse_resume_text(text)


def parse_resume_text(text: str) -> dict:
    resume = {
        "raw_text": text,
        "name": "",
        "phone": "",
        "email": "",
        "skills": [],
        "experience_years": 0,
        "education": "",
        "expected_position": "",
        "expected_city": "",
    }
    
    name_match = re.search(r'姓\s*名[：:]\s*([^\n]{2,10})', text)
    if name_match:
        resume["name"] = name_match.group(1).strip()
    
    phone_match = re.search(r'电\s*话[：:]\s*(\d{11})', text)
    if phone_match:
        resume["phone"] = phone_match.group(1)
    
    email_match = re.search(r'邮\s*箱[：:]\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
    if email_match:
        resume["email"] = email_match.group(1)
    
    skills_keywords = [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++", "C#",
        "React", "Vue", "Angular", "Node.js", "Django", "Flask", "Spring",
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "Git",
        "AI", "Machine Learning", "深度学习", "NLP", "计算机视觉",
        "Playwright", "Selenium", "Appium", "自动化测试",
    ]
    found_skills = []
    for skill in skills_keywords:
        if skill.lower() in text.lower():
            found_skills.append(skill)
    resume["skills"] = found_skills
    
    exp_match = re.search(r'(\d{1,2})\s*年', text)
    if exp_match:
        resume["experience_years"] = int(exp_match.group(1))
    
    edu_keywords = ["博士", "硕士", "本科", "大专", "高中", "中专"]
    for edu in edu_keywords:
        if edu in text:
            resume["education"] = edu
            break
    
    position_match = re.search(r'期望职位[：:]\s*([^\n]{2,20})', text)
    if position_match:
        resume["expected_position"] = position_match.group(1).strip()
    
    city_match = re.search(r'期望城市[：:]\s*([^\n]{2,10})', text)
    if city_match:
        resume["expected_city"] = city_match.group(1).strip()
    
    return resume
