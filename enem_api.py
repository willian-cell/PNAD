# enem_api_client.py
from __future__ import annotations
import os
import sys
import json
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = os.getenv("ENEM_API_BASE", "https://api.enem.dev/v1")

def _session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3, backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET"])
    )
    s.headers.update({"Accept": "application/json"})
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

# ---------- PROVAS ----------
def list_exams() -> List[Dict[str, Any]]:
    """GET /exams -> lista todas as provas disponíveis."""
    with _session() as s:
        resp = s.get(f"{BASE_URL}/exams", timeout=20)
        resp.raise_for_status()
        data = resp.json()
        # alguns catálogos retornam {"items": [...]} — tratamos os dois formatos
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        if isinstance(data, list):
            return data
        return [data]

def get_exam_by_year(year: int) -> Optional[Dict[str, Any]]:
    """Filtra a prova pelo ano."""
    exams = list_exams()
    for e in exams:
        if int(e.get("year", -1)) == int(year):
            return e
    return None

# ---------- QUESTÕES (ajuste os parâmetros conforme a doc que você está usando) ----------
def list_questions(**params) -> List[Dict[str, Any]]:
    """
    GET /questions
    Ex.: list_questions(year=2020, discipline="ciencias-humanas", language="ingles", page=1)
    """
    with _session() as s:
        resp = s.get(f"{BASE_URL}/questions", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        if isinstance(data, list):
            return data
        return [data]

def get_question(question_id: str | int) -> Dict[str, Any]:
    """GET /questions/{id}"""
    with _session() as s:
        resp = s.get(f"{BASE_URL}/questions/{question_id}", timeout=20)
        resp.raise_for_status()
        return resp.json()

# ---------- utilidade ----------
def pretty(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)

# ---------- CLI simples ----------
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Cliente simples da ENEM API")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("exams", help="Listar provas")
    p_exam = sub.add_parser("exam", help="Buscar prova por ano")
    p_exam.add_argument("--year", type=int, required=True)

    p_qs = sub.add_parser("questions", help="Listar questões (passe filtros da API)")
    p_qs.add_argument("--year", type=int)
    p_qs.add_argument("--discipline")
    p_qs.add_argument("--language")
    p_qs.add_argument("--page", type=int)

    p_q = sub.add_parser("question", help="Obter questão por ID")
    p_q.add_argument("--id", required=True)

    args = ap.parse_args()

    try:
        if args.cmd == "exams":
            print(pretty(list_exams()))
        elif args.cmd == "exam":
            exam = get_exam_by_year(args.year)
            if not exam:
                sys.exit(f"Nenhuma prova encontrada para {args.year}.")
            print(pretty(exam))
        elif args.cmd == "questions":
            params = {
                k: v for k, v in vars(args).items()
                if k in {"year", "discipline", "language", "page"} and v is not None
            }
            print(pretty(list_questions(**params)))
        elif args.cmd == "question":
            print(pretty(get_question(args.id)))
    except requests.HTTPError as e:
        msg = f"Erro HTTP {e.response.status_code}: {e.response.text}"
        sys.exit(msg)
    except requests.RequestException as e:
        sys.exit(f"Erro de rede: {e}")
