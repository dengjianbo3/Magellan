"""
Export Router
报告导出路由

Phase 4: 迁移自 main.py 的报告导出端点
- PDF导出
- Word导出
- Excel导出
- 图表生成
"""
import os
import hashlib
import tempfile
from urllib.parse import quote
from typing import Dict, Any, Optional, Callable

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# Dependencies - will be set from main.py
_get_report_func: Optional[Callable] = None


def set_get_report_func(func: Callable):
    """Set the report retrieval function from main.py"""
    global _get_report_func
    _get_report_func = func
    print("[export.py] Report retrieval function set")


def _get_report(report_id: str) -> Optional[Dict[str, Any]]:
    """Get report data using injected function"""
    if _get_report_func:
        return _get_report_func(report_id)
    raise HTTPException(status_code=500, detail="Report storage not initialized")


def _prepare_chart_data(report: Dict[str, Any], chart_type: str) -> Dict[str, Any]:
    """
    Prepare chart data from report based on chart type
    """
    preliminary_im = report.get('preliminary_im', {})
    market_analysis = report.get('market_analysis', {})
    team_analysis = report.get('team_analysis', {})

    if chart_type == 'revenue':
        return {
            'years': [2021, 2022, 2023],
            'revenue': [1000000, 1500000, 2200000]
        }

    elif chart_type == 'profit':
        return {
            'years': [2021, 2022, 2023],
            'gross_margin': [0.45, 0.52, 0.58],
            'net_margin': [0.15, 0.22, 0.28]
        }

    elif chart_type == 'financial_health':
        return {
            'liquidity': 0.75,
            'solvency': 0.68,
            'profitability': 0.72,
            'efficiency': 0.65,
            'growth': 0.80
        }

    elif chart_type == 'market_share':
        return {
            'companies': [report.get('company_name', 'Target'), 'Competitor A', 'Competitor B', 'Others'],
            'shares': [15, 25, 20, 40]
        }

    elif chart_type == 'market_growth':
        return {
            'years': [2019, 2020, 2021, 2022, 2023],
            'market_size': [500, 650, 850, 1100, 1400],
            'growth_rate': [None, 30, 31, 29, 27]
        }

    elif chart_type == 'risk_matrix':
        risks_data = preliminary_im.get('risks', [])
        if isinstance(risks_data, list) and risks_data:
            risks = []
            for risk in risks_data[:5]:
                if isinstance(risk, dict):
                    risks.append({
                        'name': risk.get('name', 'Unknown'),
                        'probability': 0.5,
                        'impact': 0.6
                    })
            return risks if risks else [{'name': 'Sample Risk', 'probability': 0.5, 'impact': 0.5}]
        return [{'name': 'Market Risk', 'probability': 0.6, 'impact': 0.7}]

    elif chart_type == 'team_radar':
        return {
            'technical': 0.8,
            'market': 0.7,
            'leadership': 0.75,
            'execution': 0.72,
            'finance': 0.65,
            'innovation': 0.78
        }

    else:
        raise ValueError(f"Unknown chart type: {chart_type}")


@router.get("/{report_id}/export/pdf")
async def export_report_to_pdf(report_id: str, language: str = "zh"):
    """
    Export a report to PDF format.

    Args:
        report_id: 报告ID
        language: 语言设置 ("zh" or "en")

    Returns:
        PDF file as downloadable response
    """
    from ...exporters.pdf_generator import generate_pdf_report

    report = _get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        temp_dir = tempfile.gettempdir()
        company_name = report.get('company_name', 'Company').replace(' ', '_')
        pdf_filename = f"{company_name}_Report_{report_id[:8]}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)

        print(f"[PDF_EXPORT] Generating PDF for report {report_id}, language={language}", flush=True)
        generate_pdf_report(report, pdf_path, language=language)
        print(f"[PDF_EXPORT] PDF generated successfully: {pdf_path}", flush=True)

        encoded_filename = quote(pdf_filename)
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=pdf_filename,
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
            }
        )

    except Exception as e:
        print(f"[PDF_EXPORT] Error generating PDF: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF: {str(e)}"
        )


@router.get("/{report_id}/export/word")
async def export_report_to_word(report_id: str, language: str = "zh"):
    """
    Export a report to Word format.

    Args:
        report_id: 报告ID
        language: 语言设置 ("zh" or "en")

    Returns:
        Word file as downloadable response
    """
    from ...exporters.word_generator import generate_word_report

    report = _get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        temp_dir = tempfile.gettempdir()
        company_name = report.get('company_name', 'Company').replace(' ', '_')
        word_filename = f"{company_name}_Report_{report_id[:8]}.docx"
        word_path = os.path.join(temp_dir, word_filename)

        print(f"[WORD_EXPORT] Generating Word for report {report_id}, language={language}", flush=True)
        generate_word_report(report, word_path, language=language)
        print(f"[WORD_EXPORT] Word generated successfully: {word_path}", flush=True)

        encoded_filename = quote(word_filename)
        return FileResponse(
            path=word_path,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=word_filename,
            headers={
                "Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"
            }
        )

    except Exception as e:
        print(f"[WORD_EXPORT] Error generating Word: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Word: {str(e)}"
        )


@router.get("/{report_id}/export/excel")
async def export_report_to_excel(report_id: str, language: str = "zh"):
    """
    Export a report to Excel format.

    Args:
        report_id: 报告ID
        language: 语言设置 ("zh" or "en")

    Returns:
        Excel file as downloadable response
    """
    from ...exporters.excel_generator import generate_excel_report

    report = _get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        temp_dir = tempfile.gettempdir()
        company_name = report.get('company_name', 'Company').replace(' ', '_')
        excel_filename = f"{company_name}_Report_{report_id[:8]}.xlsx"
        excel_path = os.path.join(temp_dir, excel_filename)

        print(f"[EXCEL_EXPORT] Generating Excel for report {report_id}, language={language}", flush=True)
        generate_excel_report(report, excel_path, language=language)
        print(f"[EXCEL_EXPORT] Excel generated successfully: {excel_path}", flush=True)

        return FileResponse(
            path=excel_path,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=excel_filename,
            headers={
                "Content-Disposition": f'attachment; filename="{excel_filename}"'
            }
        )

    except Exception as e:
        print(f"[EXCEL_EXPORT] Error generating Excel: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate Excel: {str(e)}"
        )


@router.get("/{report_id}/charts/{chart_type}")
async def generate_report_chart(report_id: str, chart_type: str, language: str = "zh"):
    """
    Generate chart for a specific report.

    Args:
        report_id: Report ID
        chart_type: Type of chart (revenue, profit, financial_health, market_share, market_growth, risk_matrix, team_radar)
        language: Language setting ("zh" or "en")

    Returns:
        PNG image of the chart
    """
    from ...exporters.chart_generator import generate_chart_for_report

    report = _get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    try:
        chart_data = _prepare_chart_data(report, chart_type)

        temp_dir = tempfile.gettempdir()
        safe_id = hashlib.md5(report_id.encode('utf-8')).hexdigest()[:12]
        chart_filename = f"chart_{safe_id}_{chart_type}.png"
        chart_path = os.path.join(temp_dir, chart_filename)

        print(f"[CHART] Generating {chart_type} chart for report {report_id}, language={language}", flush=True)
        generate_chart_for_report(chart_type, chart_data, chart_path, language=language)
        print(f"[CHART] Chart generated successfully: {chart_path}", flush=True)

        return FileResponse(
            path=chart_path,
            media_type='image/png',
            filename=chart_filename,
            headers={
                "Content-Disposition": f'inline; filename="{chart_filename}"'
            }
        )

    except Exception as e:
        print(f"[CHART] Error generating chart: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate chart: {str(e)}"
        )
