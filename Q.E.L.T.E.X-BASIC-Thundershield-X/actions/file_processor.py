import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

try:
    from google import genai
    from google.genai import types as gtypes
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

def _get_api_key() -> str:
    """Fetches the API key dynamically on each call to prevent caching and thread-locking."""
    try:
        config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    except Exception:
        return ""
    if not config_path.exists():
        print(f"[qeltex] ❌ Configuration file missing: {config_path}")
        return ""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("gemini_api_key", "")
    except Exception as e:
        print(f"[qeltex] ❌ Error reading api_keys.json: {e}")
        return ""

def _gemini_client():
    if not HAS_GEMINI_SDK:
        print("[qeltex] ❌ Missing required installation: 'google-genai' is absent.")
        print("[qeltex] 👉 Please execute command: pip install google-genai")
        raise RuntimeError("The module 'google-genai' is missing.")
    
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("Gemini API key is missing, Thundershield.")
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        raise RuntimeError(f"Could not initialize Gemini client: {e}")

def _detect_type(path: Path) -> str:
    if not path: return "unknown"
    try: clean_path = Path(path) if not isinstance(path, Path) else path
    except Exception: return "unknown"
    if not clean_path.suffix: return "unknown"
    ext = clean_path.suffix.lower().lstrip(".")
    image_exts = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "svg", "ico"}
    video_exts = {"mp4", "avi", "mov", "mkv", "wmv", "flv", "webm", "m4v", "3gp"}
    audio_exts = {"mp3", "wav", "ogg", "m4a", "aac", "flac", "wma", "opus"}
    code_exts  = {"py", "js", "ts", "jsx", "tsx", "html", "css", "java", "c", "cpp", "cs", "go", "rs", "rb", "php", "swift", "kt", "sh", "bash", "ps1", "lua", "r", "m", "sql", "yaml", "toml"}
    archive_exts = {"zip", "rar", "tar", "gz", "7z", "bz2", "xz"}
    if ext in image_exts:  return "image"
    if ext in video_exts:  return "video"
    if ext in audio_exts:  return "audio"
    if ext in code_exts:   return "code"
    if ext in archive_exts: return "archive"
    if ext == "pdf":       return "pdf"
    if ext in ("docx", "doc"): return "docx"
    if ext in ("txt", "md", "rst", "log"): return "text"
    if ext in ("csv", "tsv"): return "csv"
    if ext in ("xlsx", "xls", "ods"): return "excel"
    if ext == "json":      return "json"
    if ext == "xml":       return "xml"
    if ext in ("pptx", "ppt"): return "pptx"
    return "unknown"

def _file_size_str(path: Path) -> str:
    if not path: return "-- B"
    try:
        clean_path = Path(path) if not isinstance(path, Path) else path
        if not clean_path.exists(): return "-- B"
        size = clean_path.stat().st_size
        if size < 1024:        return f"{size} B"
        if size < 1024**2:     return f"{size/1024:.1f} KB"
        if size < 1024**3:     return f"{size/1024**2:.1f} MB"
        return f"{size/1024**3:.1f} GB"
    except Exception: return "-- B"

def _output_path(src: Path, suffix: str, new_ext: str = None) -> Path:
    try:
        clean_src = Path(src) if not isinstance(src, Path) else src
        ext  = new_ext or clean_src.suffix
        name = f"{clean_src.stem}_{suffix}{ext}"
        return clean_src.parent / name
    except Exception: return Path(src)

def _process_image(path: Path, action: str, params: dict, speak=None) -> str:
    try:
        from PIL import Image
        HAS_PILLOW = True
    except ImportError: HAS_PILLOW = False
    if not HAS_PILLOW:
        return "Pillow is not installed."
    action = str(action or "describe").lower().strip()
    if action in ("describe", "ocr", "analyze", "read", "extract_text"):
        try:
            if not path.exists(): return f"Image file not found: {path.name}"
            client = _gemini_client()
            with open(path, "rb") as f: img_bytes = f.read()
            img_part = gtypes.Part.from_bytes(
                data=img_bytes,
                mime_type="image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else f"image/{path.suffix.lower().lstrip('.')}"
            )
            prompt = {
                "describe": "Describe this image in detail.",
                "ocr":      "Extract all text visible in this image. Return only the text, formatted clearly.",
                "analyze":  "Analyze this image thoroughly: objects, colors, composition, any text, context.",
                "read":     "Read all text in this image, preserving structure and formatting.",
                "extract_text": "Extract all text from this image.",
            }.get(action, "Describe this image.")
            clean_params = params if isinstance(params, dict) else {}
            if clean_params.get("instruction"): prompt = str(clean_params["instruction"])
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, img_part],
                config=gtypes.GenerateContentConfig(
                    system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian. Your tone shall be loyal, high-tech, sharp and slightly formal."
                )
            )
            result = response.text.strip() if response.text else "No analysis results generated."
            if len(result) > 500 and clean_params.get("save", True):
                out = _output_path(path, "result", ".txt")
                try: out.write_text(result, encoding="utf-8")
                except Exception: pass
            return result
        except Exception as e: return f"Image analysis failed: {e}"
    if action == "resize":
        try:
            width = int(params.get("width", 0))
            height = int(params.get("height", 0))
            scale = float(params.get("scale", 0))
            if not path.exists(): return f"Image file not found: {path.name}"
            img = Image.open(path)
            w, h = img.size
            if scale > 0: new_size = (int(w * scale), int(h * scale))
            elif width and height: new_size = (width, height)
            elif width: new_size = (width, int(h * width / w))
            elif height: new_size = (int(w * height / h), height)
            else: return "Please specify width, height, or scale."
            out = _output_path(path, f"resized_{new_size[0]}x{new_size[1]}")
            img.resize(new_size, Image.Resampling.LANCZOS).save(out)
            return f"Resized to {new_size[0]}x{new_size[1]}. Saved: {out.name}"
        except Exception as e: return f"Image resizing failed: {e}"
    if action == "convert":
        try:
            fmt = str(params.get("format", "png")).lower().strip(".")
            if not path.exists(): return f"Image file not found: {path.name}"
            img = Image.open(path).convert("RGB") if fmt in ("jpg", "jpeg") else Image.open(path)
            out = _output_path(path, "converted", f".{fmt}")
            img.save(out)
            return f"Converted to {fmt.upper()}. Saved: {out.name}"
        except Exception as e: return f"Conversion failed: {e}"
    if action == "compress":
        try:
            quality = int(params.get("quality", 70))
            if not path.exists(): return f"Image file not found: {path.name}"
            img = Image.open(path).convert("RGB")
            out = _output_path(path, f"compressed_q{quality}", ".jpg")
            img.save(out, "JPEG", quality=quality, optimize=True)
            return f"Compression completed. Saved: {out.name}"
        except Exception as e: return f"Compression failed: {e}"
    if action == "info":
        try:
            if not path.exists(): return f"Image file not found: {path.name}"
            img = Image.open(path)
            return f"Image Information: {img.format}, {img.size[0]}x{img.size[1]}px, mode: {img.mode}"
        except Exception as e: return f"Failed: {e}"
    return "Unknown action."

def _process_pdf(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "summarize").lower().strip()
    def _extract_pdf_text(max_chars=50000) -> str:
        if not path.exists(): return ""
        text = ""
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages: text += (page.extract_text() or "") + "\n"
            return text[:max_chars]
        except Exception: pass
        try:
            import PyPDF2
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages: text += (page.extract_text() or "") + "\n"
            return text[:max_chars]
        except Exception: pass
        return "__MISSING__"
    if action in ("summarize", "extract_text", "translate_hint", "analyze", "reformat"):
        text = _extract_pdf_text()
        if text == "__MISSING__": return "Required PDF libraries are not installed."
        if not text.strip(): return "Could not extract text from the PDF file."
        clean_params = params if isinstance(params, dict) else {}
        if action == "extract_text":
            try:
                out = _output_path(path, "text", ".txt")
                out.write_text(text, encoding="utf-8")
                return f"Text extracted. Saved: {out.name}"
            except Exception as e: return f"Could not save file: {e}"
        prompt_map = {
            "summarize": f"Summarize this PDF concisely:\n\n{text}",
            "analyze": f"Analyze this document thoroughly:\n\n{text}",
            "translate_hint": f"What language is this and what does it say?:\n\n{text}",
            "reformat": f"Reformat this text cleanly:\n\n{text}",
        }
        try:
            if not path.exists(): return f"PDF file not found: {path.name}"
            client = _gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_map.get(action, f"Analyze:\n\n{text}"),
                config=gtypes.GenerateContentConfig(
                    system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian."
                )
            )
            result = response.text.strip() if response.text else "No response received."
            if len(result) > 600 and clean_params.get("save", True):
                out = _output_path(path, action, ".txt")
                try: out.write_text(result, encoding="utf-8")
                except Exception: pass
            return result
        except Exception as e: return f"Q.E.L.T.E.X processing failed: {e}"
        
    if action == "info":
        try:
            if not path.exists(): return f"PDF file not found: {path.name}"
            return f"PDF size: {_file_size_str(path)}"
        except Exception: return f"PDF size: {_file_size_str(path)}"
        
    if action == "to_word":
        text = _extract_pdf_text()
        if not text or text == "__MISSING__": return "Could not extract text."
        try:
            from docx import Document
            doc = Document()
            doc.add_heading(path.stem, 0)
            for para in text.split("\n\n"):
                if para.strip(): doc.add_paragraph(para.strip())
            out = _output_path(path, "converted", ".docx")
            doc.save(out)
            return f"Converted to Word document. Saved: {out.name}"
        except Exception as e: return f"Conversion failed: {e}"
        
    return f"Unknown PDF action: '{action}'."

def _process_text_doc(path: Path, file_type: str, action: str, params: dict, speak=None) -> str:
    action = str(action or "summarize").lower().strip()
    def _read_content() -> str:
        if not path.exists(): return ""
        if str(file_type).lower() == "docx":
            try:
                from docx import Document
                doc = Document(path)
                return "\n".join(p.text for p in doc.paragraphs)
            except Exception as e: return f"Reading failed: {e}"
        else:
            try: return path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e: return f"Reading text file failed: {e}"
    content = _read_content()
    if not content or not content.strip():
        return "The file appears to be empty or unreadable, Thundershield."
    if action == "word_count":
        try:
            words = len(content.split())
            chars = len(content)
            lines = content.count("\n")
            return f"Statistics: {words} words, {chars} characters, {lines} lines."
        except Exception as e: return f"Could not calculate text statistics: {e}"
    if action == "extract_text":
        if file_type != "txt":
            try:
                out = _output_path(path, "extracted", ".txt")
                out.write_text(content, encoding="utf-8")
                return f"Text extracted. File saved: {out.name}"
            except Exception as e: return f"Could not save extracted text: {e}"
        return content[:2000]
    clean_params = params if isinstance(params, dict) else {}
    instruction = str(clean_params.get("instruction", "")).strip()
    prompt_map = {
        "summarize":  f"Summarize this document concisely:\n\n{content[:40000]}",
        "analyze":    f"Analyze this document:\n\n{content[:40000]}",
        "reformat":   f"Reformat this text with clean structure:\n\n{content[:40000]}",
        "fix":        f"Fix grammar, spelling and style issues:\n\n{content[:40000]}",
        "translate_hint": f"What language is this and what does it say? Summarize:\n\n{content[:10000]}",
        "to_bullet":  f"Convert this text into a clear bullet-point summary:\n\n{content[:40000]}",
        "custom":     f"{instruction if instruction else 'Analyze text:'}\n\n{content[:40000]}",
    }
    if action not in prompt_map: action = "custom"
    try:
        if not path.exists(): return f"Document file not found: {path.name}"
        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_map[action],
            config=gtypes.GenerateContentConfig(
                system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian. Your tone shall be loyal, high-tech, sharp and slightly formal."
            )
        )
        result = response.text.strip() if response.text else "No response generated."
        if len(result) > 600 and clean_params.get("save", True):
            out = _output_path(path, action, ".txt")
            try: out.write_text(result, encoding="utf-8")
            except Exception: pass
        return result
    except Exception as e: return f"Q.E.L.T.E.X processing failed: {e}"

def _process_data(path: Path, file_type: str, action: str, params: dict, speak=None) -> str:
    try:
        import pandas as pd
        HAS_PANDAS = True
    except ImportError: HAS_PANDAS = False
    if not HAS_PANDAS: return "pandas and openpyxl are not installed."
    action = str(action or "analyze").lower().strip()
    try:
        if not path.exists(): return f"Data file not found: {path.name}"
        if str(file_type).lower() == "csv": df = pd.read_csv(path, encoding="utf-8", errors="replace")
        else: df = pd.read_excel(path)
    except Exception as e: return f"Could not read the file: {e}"
    if action == "info":
        try: return f"Rows: {len(df)}, Columns: {len(df.columns)}\nColumns: {', '.join(df.columns.tolist())}\nSize: {_file_size_str(path)}"
        except Exception as e: return f"Could not retrieve file information: {e}"
    if action == "stats":
        try: return f"Statistics:\n{df.describe(include='all').to_string()[:2000]}"
        except Exception as e: return f"Statistics generation failed: {e}"
    if action == "analyze":
        try:
            preview = df.head(50).to_string()
            prompt = f"Analyze this dataset. Columns: {list(df.columns)}\nRows: {len(df)}\nPreview:\n{preview}"
            client = _gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian."
                )
            )
            return response.text.strip() if response.text else "No data analysis generated."
        except Exception as e: return f"Q.E.L.T.E.X data analysis failed: {e}"
    if action in ("convert", "to_csv", "to_excel", "to_json"):
        clean_params = params if isinstance(params, dict) else {}
        fmt = {"to_csv": "csv", "to_excel": "xlsx", "to_json": "json", "convert": clean_params.get("format", "csv")}.get(action, "csv")
        try:
            if fmt == "csv":
                out = _output_path(path, "converted", ".csv")
                df.to_csv(out, index=False, encoding="utf-8")
            elif fmt == "xlsx":
                out = _output_path(path, "converted", ".xlsx")
                df.to_excel(out, index=False)
            elif fmt == "json":
                out = _output_path(path, "converted", ".json")
                df.to_json(out, orient="records", force_ascii=False, indent=2)
            return f"Converted to {fmt.upper()}. File saved: {out.name}"
        except Exception as e: return f"Conversion failed: {e}"
    if action == "filter":
        clean_params = params if isinstance(params, dict) else {}
        col = clean_params.get("column", "")
        value = clean_params.get("value", "")
        condition = str(clean_params.get("condition", "equals")).lower().strip()
        if not col or col not in df.columns: return f"Column '{col}' was not found."
        try:
            if condition == "equals": filtered = df[df[col] == value]
            elif condition == "contains": filtered = df[df[col].astype(str).str.contains(str(value), case=False)]
            elif condition == "gt": filtered = df[df[col] > float(value)]
            elif condition == "lt": filtered = df[df[col] < float(value)]
            else: filtered = df[df[col] == value]
            out = _output_path(path, "filtered", ".csv")
            filtered.to_csv(out, index=False)
            return f"Filtering completed: {len(filtered)} rows match. Saved: {out.name}"
        except Exception as e: return f"Filtering failed: {e}"
    if action == "sort":
        clean_params = params if isinstance(params, dict) else {}
        col = clean_params.get("column", df.columns if len(df.columns) > 0 else "")
        asc = bool(clean_params.get("ascending", True))
        try:
            sorted_df = df.sort_values(col, ascending=asc)
            out = _output_path(path, "sorted", path.suffix)
            if str(path.suffix).lower() == ".csv": sorted_df.to_csv(out, index=False)
            else: sorted_df.to_excel(out, index=False)
            return f"Sorted by '{col}'. Saved: {out.name}"
        except Exception as e: return f"Sorting failed: {e}"
    return "Unknown data action."

def _process_json(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "analyze").lower().strip()
    try:
        if not path.exists(): return f"JSON file not found: {path.name}"
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as e: return f"Invalid JSON: {e}"
    if action == "validate": return f"Valid JSON. size: {_file_size_str(path)}"
    if action == "format":
        try:
            out = _output_path(path, "formatted", ".json")
            out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return f"Formatted JSON saved: {out.name}"
        except Exception as e: return f"Could not save JSON: {e}"
    if action in ("analyze", "summarize", "extract"):
        clean_params = params if isinstance(params, dict) else {}
        preview = json.dumps(data, indent=2, ensure_ascii=False)[:8000]
        prompt = f"Task: {action} this JSON data:\n{preview}"
        if clean_params.get("instruction"): prompt = f"{clean_params['instruction']}\n\nJSON data:\n{preview}"
        try:
            client = _gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=gtypes.GenerateContentConfig(
                    system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian."
                )
            )
            return response.text.strip() if response.text else "No response generated."
        except Exception as e: return f"Q.E.L.T.E.X JSON processing failed: {e}"

def _process_code(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "explain").lower().strip()
    if not path.exists(): return f"Source code file not found: {path.name}"
    try: content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e: return f"Could not read source code file: {e}"
    ext = path.suffix.lower().lstrip(".")
    if action == "run":
        if ext == "py":
            try:
                result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=30)
                out = (result.stdout or "") + (result.stderr or "")
                return f"Output:\n{out[:2000]}" if out.strip() else "No output (empty execution)."
            except subprocess.TimeoutExpired: return "Execution aborted due to timeout (30s)."
            except Exception as e: return f"Execution failed: {e}"
        return f"Direct execution is not supported for .{ext} files."
    if action == "info":
        lines = content.count("\n")
        words = len(content.split())
        return f"Source code: {lines} lines, {words} words, {_file_size_str(path)}"
    prompt_map = {
        "explain":   f"Explain this {ext} code clearly:\n\n```{ext}\n{content[:30000]}\n```",
        "review":    f"Review this {ext} code for bugs:\n\n```{ext}\n{content[:30000]}\n```",
        "fix":       f"Fix bugs in this {ext} code:\n\n```{ext}\n{content[:30000]}\n```",
        "optimize":  f"Optimize this {ext} code:\n\n```{ext}\n{content[:30000]}\n```",
    }
    clean_params = params if isinstance(params, dict) else {}
    if action not in prompt_map: prompt = f"{action}\n\n```{ext}\n{content[:30000]}\n```"
    else: prompt = prompt_map[action]
    try:
        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=gtypes.GenerateContentConfig(
                system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian. Your tone shall be loyal, high-tech, sharp and slightly formal."
            )
        )
        result = response.text.strip() if response.text else "No response received."
        if action in ("fix", "optimize", "document") and clean_params.get("save", True):
            out = _output_path(path, action)
            code_match = re.search(r"```(?:\w+)?\n(.*?)```", result, re.DOTALL)
            code_to_save = code_match.group(1) if (code_match and len(code_match.groups()) >= 1) else result
            try: out.write_text(code_to_save, encoding="utf-8")
            except Exception: pass
        return result
    except Exception as e: return f"Q.E.L.T.E.X code processing failed: {e}"

def _process_audio(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "transcribe").lower().strip()
    if not path.exists(): return f"Audio file not found: {path.name}"
    if action == "info":
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(path)
            duration = len(audio) / 1000
            mins, secs = divmod(int(duration), 60)
            return f"Audio Information: {mins}m {secs}s, {audio.channels} channels"
        except Exception: return f"Audio file size: {_file_size_str(path)}"
    clean_params = params if isinstance(params, dict) else {}
    if action == "transcribe":
        try:
            client = _gemini_client()
            content = path.read_bytes()
            mime = {"mp3": "audio/mp3", "wav": "audio/wav", "ogg": "audio/ogg", "m4a": "audio/mp4"}.get(path.suffix.lstrip(".").lower(), "audio/mpeg")
            audio_part = gtypes.Part.from_bytes(data=content, mime_type=mime)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=["Transcribe speech accurately. Use Norwegian.", audio_part],
                config=gtypes.GenerateContentConfig(
                    system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian."
                )
            )
            result = response.text.strip() if response.text else "No transcription generated."
            if clean_params.get("save", True) and response.text:
                out = _output_path(path, "transcript", ".txt")
                try: out.write_text(result, encoding="utf-8")
                except Exception: pass
            return result
        except Exception as e: return f"Transcription failed: {e}"
    return "Unknown audio action."

def _process_video(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "info").lower().strip()
    if action == "info":
        try:
            result = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(path)], capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout) if result.stdout else {}
            fmt = data.get("format", {})
            duration = float(fmt.get("duration", 0))
            mins, secs = divmod(int(duration), 60)
            return f"Video: {mins}m {secs}s, size: {_file_size_str(path)}"
        except Exception: return f"Video size: {_file_size_str(path)}"
    if action == "transcribe":
        try:
            tmp_audio = Path(tempfile.gettempdir()) / f"qeltex_tmp_{int(time.time())}.mp3"
            subprocess.run(["ffmpeg", "-i", str(path), "-q:a", "0", "-map", "a", str(tmp_audio), "-y"], capture_output=True, timeout=300)
            return _process_audio(tmp_audio, "transcribe", params, speak)
        except Exception as e: return f"Video transcription failed: {e}"
        finally:
            try:
                if tmp_audio.exists(): tmp_audio.unlink(missing_ok=True)
            except Exception: pass
    return "Unknown video action."

def _process_archive(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "list").lower().strip()
    if action == "list":
        try:
            import zipfile, tarfile
            ext = path.suffix.lower()
            if ext == ".zip":
                with zipfile.ZipFile(path) as z: names = z.namelist()
            elif ext in (".tar", ".gz"):
                with tarfile.open(path) as t: names = t.getnames()
            else: return f"Unsupported archive: {ext}"
            return f"Archive contains {len(names)} files:\n" + "\n".join(names[:10])
        except Exception as e: return f"Failed: {e}"
    if action == "extract":
        try:
            clean_params = params if isinstance(params, dict) else {}
            dest = Path(clean_params.get("destination", str(path.parent / path.stem)))
            dest.mkdir(parents=True, exist_ok=True)
            shutil.unpack_archive(path, dest)
            return f"Extracted to: {dest}"
        except Exception as e: return f"Extraction failed: {e}"
    return "Unknown archive action."

def _process_pptx(path: Path, action: str, params: dict, speak=None) -> str:
    action = str(action or "summarize").lower().strip()
    try:
        from pptx import Presentation
        prs = Presentation(path)
        text = []
        for i, slide in enumerate(prs.slides, 1):
            slide_text = f"\n--- Slide {i} ---\n"
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip(): slide_text += shape.text.strip() + "\n"
            text.append(slide_text)
        full_text = "\n".join(text)
    except Exception: return "PowerPoint file unreadable or python-pptx missing."
    if action == "extract_text":
        try:
            out = _output_path(path, "text", ".txt")
            out.write_text(full_text, encoding="utf-8")
            return f"Text extracted. Saved: {out.name}"
        except Exception as e: return f"Could not save: {e}"
    try:
        client = _gemini_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Analyze this presentation:\n{full_text[:30000]}",
            config=gtypes.GenerateContentConfig(
                system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian."
            )
        )
        return response.text.strip() if response.text else "No response generated."
    except Exception as e: return f"Q.E.L.T.E.X failed: {e}"

def file_processor(parameters: dict, player=None, speak=None) -> str:
    clean_parameters = parameters or {}
    if isinstance(clean_parameters, str):
        try: clean_parameters = json.loads(clean_parameters)
        except Exception: clean_parameters = {"action": "auto", "file_path": parameters}
    if not isinstance(clean_parameters, dict): clean_parameters = {}
    file_path_str = str(clean_parameters.get("file_path", "")).strip()
    if not file_path_str: return "No file path provided."
    try: path = Path(file_path_str)
    except Exception: return "Invalid file path format."
    if not path.exists(): return f"File not found: {file_path_str}"
    if not path.is_file(): return f"Specified path is not a file: {file_path_str}"
    file_type = _detect_type(path)
    action = str(clean_parameters.get("action") or "").lower().strip()
    instruction = str(clean_parameters.get("instruction", "")).strip()
    params = {**clean_parameters, "instruction": instruction}
    
    if file_type == "unknown":
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:10000]
            client = _gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"File: {path.name}\nContent:\n{content}\nTask: {action or instruction or 'Describe.'}",
                config=gtypes.GenerateContentConfig(
                    system_instruction="You are Q.E.L.T.E.X. Communicate in flawless Norwegian."
                )
            )
            return response.text.strip() if response.text else "Could not determine analysis."
        except Exception as e: return f"Unknown type. Failed: {e}"

    dispatch = {
        "image":   _process_image,
        "pdf":     _process_pdf,
        "docx":    lambda p, a, pm, s: _process_text_doc(p, "docx", a, pm, s),
        "text":    lambda p, a, pm, s: _process_text_doc(p, "text", a, pm, s),
        "csv":     lambda p, a, pm, s: _process_data(p, "csv",   a, pm, s),
        "excel":   lambda p, a, pm, s: _process_data(p, "excel", a, pm, s),
        "json":    _process_json,
        "xml":     lambda p, a, pm, s: _process_json(p, a, pm, s),  
        "code":    _process_code,
        "audio":   _process_audio,
        "video":   _process_video,
        "archive": _process_archive,
        "pptx":    _process_pptx,
    }
    
    handler = dispatch.get(file_type)
    if not handler: return f"Unsupported file type: {file_type}"
    
    try:
        result = handler(path, action, params, speak)
        return result or "Executed."
    except Exception as e: return f"Processing failed: {e}"