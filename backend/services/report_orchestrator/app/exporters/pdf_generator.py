"""
PDF Report Generator
PDF报告生成器

Uses ReportLab to generate professional investment analysis reports in PDF format.
使用ReportLab生成专业的投资分析报告PDF格式。
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from typing import Dict, Any, List
import os


class PDFReportGenerator:
    """
    PDF报告生成器

    Features:
    - 中英文支持
    - 专业排版
    - 多章节结构
    - 表格和列表
    - 图表嵌入（预留）
    """

    def __init__(self, language: str = "zh"):
        """
        初始化PDF生成器

        Args:
            language: 语言 ("zh" 中文, "en" 英文)
        """
        self.language = language
        self.page_size = A4
        
        # 注册中文字体
        self.chinese_font = self._register_chinese_font()
        self.chinese_font_bold = self.chinese_font  # CJK字体通常不区分Bold，使用同一字体
        
        self.styles = self._setup_styles()
    
    def _register_chinese_font(self) -> str:
        """
        注册中文字体，返回可用的字体名称
        
        Returns:
            字体名称 (如果中文字体不可用，返回Helvetica)
        """
        # 尝试使用 Noto Sans CJK 中文字体
        chinese_font_paths = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            '/usr/local/share/fonts/NotoSansCJK-Regular.ttc',
        ]
        
        for font_path in chinese_font_paths:
            if os.path.exists(font_path):
                try:
                    # TTC 文件需要指定 subfontIndex (0 是第一个字体)
                    pdfmetrics.registerFont(TTFont('NotoSansCJK', font_path, subfontIndex=0))
                    print(f"[PDFGenerator] Registered Chinese font: {font_path}")
                    return 'NotoSansCJK'
                except Exception as e:
                    print(f"[PDFGenerator] Failed to register font {font_path}: {e}")
                    continue
        
        # 如果是中文但没有找到中文字体，打印警告
        if self.language == "zh":
            print("[PDFGenerator] WARNING: Chinese font not found, PDF may show garbled text for Chinese characters")
        
        return 'Helvetica'  # 回退到默认字体

    def _setup_styles(self) -> Dict[str, ParagraphStyle]:
        """设置样式"""
        styles = getSampleStyleSheet()
        
        # 根据语言选择字体
        title_font = self.chinese_font if self.language == "zh" else 'Helvetica-Bold'
        body_font = self.chinese_font if self.language == "zh" else 'Helvetica'

        # 标题样式
        if 'ReportTitle' not in styles:
            styles.add(ParagraphStyle(
                name='ReportTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName=title_font
            ))

        # 章节标题
        if 'ChapterTitle' not in styles:
            styles.add(ParagraphStyle(
                name='ChapterTitle',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=colors.HexColor('#2c3e50'),
                spaceBefore=20,
                spaceAfter=12,
                fontName=title_font
            ))

        # 小节标题
        if 'SectionTitle' not in styles:
            styles.add(ParagraphStyle(
                name='SectionTitle',
                parent=styles['Heading3'],
                fontSize=14,
                textColor=colors.HexColor('#34495e'),
                spaceBefore=12,
                spaceAfter=6,
                fontName=title_font
            ))

        # 正文样式
        if 'BodyText' not in styles:
            styles.add(ParagraphStyle(
                name='BodyText',
                parent=styles['Normal'],
                fontSize=11,
                leading=16,
                textColor=colors.HexColor('#2c3e50'),
                alignment=TA_JUSTIFY,
                spaceAfter=10,
                fontName=body_font
            ))

        # 重点文本
        if 'Highlight' not in styles:
            styles.add(ParagraphStyle(
                name='Highlight',
                parent=styles['BodyText'],
                textColor=colors.HexColor('#e74c3c'),
                fontName=title_font
            ))

        return styles

    def generate_report(
        self,
        report_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        生成完整PDF报告

        Args:
            report_data: 报告数据
            output_path: 输出文件路径

        Returns:
            生成的PDF文件路径
        """
        # 创建PDF文档
        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.page_size,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # 构建文档内容
        story = []

        # 获取 sections（LLM生成的报告格式）
        # 数据可能在顶层或 preliminary_im 内部
        preliminary_im = report_data.get('preliminary_im', {})
        sections = report_data.get('sections') or preliminary_im.get('sections', {})

        # 1. 封面
        story.extend(self._build_cover_page(report_data))
        story.append(PageBreak())

        # 2. 目录（简化版）
        story.extend(self._build_table_of_contents(report_data))
        story.append(PageBreak())

        # 3. 执行摘要
        if preliminary_im:
            story.extend(self._build_executive_summary(preliminary_im))
            story.append(PageBreak())

        # 4. 财务分析 - 优先从 sections 获取，兼容旧格式
        financial_data = sections.get('financial') or preliminary_im.get('financial_highlights')
        if financial_data:
            story.extend(self._build_financial_section_v2(financial_data, preliminary_im))
            story.append(PageBreak())

        # 5. 市场分析 - 优先从 sections 获取，也检查 market_section
        market_data = sections.get('market') or preliminary_im.get('market_section') or report_data.get('market_analysis')
        if market_data:
            story.extend(self._build_market_section(market_data))
            story.append(PageBreak())

        # 6. 团队分析 - 优先从 sections 获取，也检查 team_section
        team_data = sections.get('team') or preliminary_im.get('team_section') or report_data.get('team_analysis')
        if team_data:
            story.extend(self._build_team_section(team_data))
            story.append(PageBreak())

        # 7. 风险评估 - 优先从 sections 获取
        risk_data = sections.get('risk')
        if risk_data:
            story.extend(self._build_risk_section_v2(risk_data))
            story.append(PageBreak())
        elif preliminary_im.get('risks'):
            story.extend(self._build_risk_section(preliminary_im))
            story.append(PageBreak())

        # 8. 结论和建议
        if preliminary_im:
            story.extend(self._build_conclusion(preliminary_im))

        # 生成PDF
        doc.build(story)

        return output_path

    def _build_financial_section_v2(self, financial_data: Dict[str, Any], im_data: Dict[str, Any]) -> List:
        """构建财务分析章节 - 支持新旧两种格式"""
        story = []

        if self.language == "en":
            story.append(Paragraph("2. Financial Analysis", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("2. 财务分析", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        # 如果是新格式 (summary 字段)
        if financial_data.get('summary'):
            summary_text = str(financial_data['summary'])
            paragraphs = summary_text.split('\n\n') if '\n\n' in summary_text else [summary_text]
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), self.styles['BodyText']))
                    story.append(Spacer(1, 0.1*inch))
        else:
            # 旧格式
            if isinstance(financial_data, dict):
                if self.language == "en":
                    story.append(Paragraph("Financial Highlights", self.styles['SectionTitle']))
                else:
                    story.append(Paragraph("财务亮点", self.styles['SectionTitle']))

                table_data = []
                if self.language == "en":
                    table_data.append(['Metric', 'Value'])
                else:
                    table_data.append(['指标', '数值'])

                for key, value in financial_data.items():
                    if key != 'summary':
                        table_data.append([str(key), str(value)])

                if len(table_data) > 1:
                    table = Table(table_data, colWidths=[3*inch, 3*inch])
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.2*inch))

        # 添加 im_data 中的财务分析
        if im_data.get('financial_analysis'):
            story.append(Paragraph(str(im_data['financial_analysis']), self.styles['BodyText']))

        return story

    def _build_risk_section_v2(self, risk_data: Dict[str, Any]) -> List:
        """构建风险评估章节 - 支持新格式"""
        story = []

        if self.language == "en":
            story.append(Paragraph("5. Risk Evaluation", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("5. 风险评估", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        # 如果是新格式 (summary 字段)
        if risk_data.get('summary'):
            summary_text = str(risk_data['summary'])
            paragraphs = summary_text.split('\n\n') if '\n\n' in summary_text else [summary_text]
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), self.styles['BodyText']))
                    story.append(Spacer(1, 0.1*inch))

        return story

    def _build_cover_page(self, report_data: Dict[str, Any]) -> List:
        """构建封面"""
        story = []

        # 添加空白
        story.append(Spacer(1, 2*inch))

        # 报告标题
        if self.language == "en":
            title = f"Investment Analysis Report"
            subtitle = f"{report_data.get('company_name', 'Company Name')}"
        else:
            title = "投资尽职调查报告"
            subtitle = report_data.get('company_name', '公司名称')

        story.append(Paragraph(title, self.styles['ReportTitle']))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph(f"<b>{subtitle}</b>", self.styles['ChapterTitle']))

        # 日期
        story.append(Spacer(1, 1*inch))
        date_str = datetime.now().strftime("%Y-%m-%d")
        if self.language == "en":
            date_text = f"Report Date: {date_str}"
        else:
            date_text = f"报告日期: {date_str}"
        story.append(Paragraph(date_text, self.styles['BodyText']))

        # 生成信息
        story.append(Spacer(1, 0.5*inch))
        if self.language == "en":
            gen_text = "Generated by Magellan AI Investment Analysis Platform"
        else:
            gen_text = "由 Magellan AI 投资分析平台生成"
        story.append(Paragraph(gen_text, self.styles['BodyText']))

        return story

    def _build_table_of_contents(self, report_data: Dict[str, Any]) -> List:
        """构建目录"""
        story = []

        if self.language == "en":
            story.append(Paragraph("Table of Contents", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("目录", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.3*inch))

        # 章节列表
        sections = []
        if self.language == "en":
            sections = [
                "1. Executive Summary",
                "2. Financial Analysis",
                "3. Market Analysis",
                "4. Team Assessment",
                "5. Risk Evaluation",
                "6. Conclusion and Recommendations"
            ]
        else:
            sections = [
                "1. 执行摘要",
                "2. 财务分析",
                "3. 市场分析",
                "4. 团队评估",
                "5. 风险评估",
                "6. 结论与建议"
            ]

        for section in sections:
            story.append(Paragraph(section, self.styles['BodyText']))
            story.append(Spacer(1, 0.1*inch))

        return story

    def _build_executive_summary(self, im_data: Dict[str, Any]) -> List:
        """构建执行摘要"""
        story = []

        if self.language == "en":
            story.append(Paragraph("1. Executive Summary", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("1. 执行摘要", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        # 投资建议
        if im_data.get('investment_recommendation'):
            if self.language == "en":
                story.append(Paragraph("Investment Recommendation", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("投资建议", self.styles['SectionTitle']))

            rec_text = str(im_data['investment_recommendation'])
            story.append(Paragraph(rec_text, self.styles['BodyText']))
            story.append(Spacer(1, 0.15*inch))

        # 关键发现
        if im_data.get('key_findings'):
            if self.language == "en":
                story.append(Paragraph("Key Findings", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("关键发现", self.styles['SectionTitle']))

            findings = im_data['key_findings']
            if isinstance(findings, list):
                for finding in findings:
                    if isinstance(finding, dict):
                        # Format dict finding
                        category = finding.get('category', 'General')
                        score = finding.get('score', 'N/A')
                        points = "; ".join(finding.get('key_points', []))
                        concerns = "; ".join(finding.get('concerns', []))
                        
                        text = f"• <b>{category} (评分: {score})</b>"
                        if points: text += f"<br/>  亮点: {points}"
                        if concerns: text += f"<br/>  关注: {concerns}"
                        
                        story.append(Paragraph(text, self.styles['BodyText']))
                    else:
                        story.append(Paragraph(f"• {finding}", self.styles['BodyText']))
            else:
                story.append(Paragraph(str(findings), self.styles['BodyText']))
            story.append(Spacer(1, 0.15*inch))

        # 投资亮点
        if im_data.get('investment_highlights'):
            if self.language == "en":
                story.append(Paragraph("Investment Highlights", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("投资亮点", self.styles['SectionTitle']))

            highlights = im_data['investment_highlights']
            if isinstance(highlights, list):
                for hl in highlights:
                    story.append(Paragraph(f"• {hl}", self.styles['BodyText']))
            else:
                story.append(Paragraph(str(highlights), self.styles['BodyText']))

        return story

    def _build_financial_section(self, im_data: Dict[str, Any]) -> List:
        """构建财务分析章节"""
        story = []

        if self.language == "en":
            story.append(Paragraph("2. Financial Analysis", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("2. 财务分析", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        fin_data = im_data.get('financial_highlights', {})

        # 财务亮点
        if fin_data:
            if self.language == "en":
                story.append(Paragraph("Financial Highlights", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("财务亮点", self.styles['SectionTitle']))

            # 创建财务指标表格
            table_data = []
            if self.language == "en":
                table_data.append(['Metric', 'Value'])
            else:
                table_data.append(['指标', '数值'])

            for key, value in fin_data.items():
                table_data.append([str(key), str(value)])

            table = Table(table_data, colWidths=[3*inch, 3*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(table)
            story.append(Spacer(1, 0.2*inch))

        # 财务分析
        if im_data.get('financial_analysis'):
            if self.language == "en":
                story.append(Paragraph("Analysis", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("分析", self.styles['SectionTitle']))

            story.append(Paragraph(str(im_data['financial_analysis']), self.styles['BodyText']))

        return story

    def _build_market_section(self, market_data: Dict[str, Any]) -> List:
        """构建市场分析章节"""
        story = []

        if self.language == "en":
            story.append(Paragraph("3. Market Analysis", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("3. 市场分析", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        # 首先检查是否有 summary 字段 (LLM生成的报告格式)
        if market_data.get('summary'):
            summary_text = str(market_data['summary'])
            # 分段落显示
            paragraphs = summary_text.split('\n\n') if '\n\n' in summary_text else [summary_text]
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), self.styles['BodyText']))
                    story.append(Spacer(1, 0.1*inch))
            return story

        # 兼容旧格式：市场规模
        if market_data.get('market_size_analysis'):
            if self.language == "en":
                story.append(Paragraph("Market Size", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("市场规模", self.styles['SectionTitle']))

            story.append(Paragraph(str(market_data['market_size_analysis']), self.styles['BodyText']))
            story.append(Spacer(1, 0.15*inch))

        # 竞争格局
        if market_data.get('competitive_landscape'):
            if self.language == "en":
                story.append(Paragraph("Competitive Landscape", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("竞争格局", self.styles['SectionTitle']))

            story.append(Paragraph(str(market_data['competitive_landscape']), self.styles['BodyText']))
            story.append(Spacer(1, 0.15*inch))

        # 市场趋势
        if market_data.get('market_trends'):
            if self.language == "en":
                story.append(Paragraph("Market Trends", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("市场趋势", self.styles['SectionTitle']))

            trends = market_data['market_trends']
            if isinstance(trends, list):
                for trend in trends:
                    story.append(Paragraph(f"• {trend}", self.styles['BodyText']))
            else:
                story.append(Paragraph(str(trends), self.styles['BodyText']))

        return story

    def _build_team_section(self, team_data: Dict[str, Any]) -> List:
        """构建团队分析章节"""
        story = []

        if self.language == "en":
            story.append(Paragraph("4. Team Assessment", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("4. 团队评估", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        # 首先检查是否有 summary 字段 (LLM生成的报告格式)
        if team_data.get('summary'):
            summary_text = str(team_data['summary'])
            # 分段落显示
            paragraphs = summary_text.split('\n\n') if '\n\n' in summary_text else [summary_text]
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para.strip(), self.styles['BodyText']))
                    story.append(Spacer(1, 0.1*inch))
            return story

        # 兼容旧格式：团队评分
        if team_data.get('experience_match_score'):
            if self.language == "en":
                score_text = f"Experience Match Score: {team_data['experience_match_score']}/10"
            else:
                score_text = f"经验匹配度评分: {team_data['experience_match_score']}/10"

            story.append(Paragraph(score_text, self.styles['Highlight']))
            story.append(Spacer(1, 0.15*inch))

        # 团队优势
        if team_data.get('strengths'):
            if self.language == "en":
                story.append(Paragraph("Team Strengths", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("团队优势", self.styles['SectionTitle']))

            strengths = team_data['strengths']
            if isinstance(strengths, list):
                for strength in strengths:
                    story.append(Paragraph(f"• {strength}", self.styles['BodyText']))
            else:
                story.append(Paragraph(str(strengths), self.styles['BodyText']))
            story.append(Spacer(1, 0.15*inch))

        # 改进建议
        if team_data.get('recommendations'):
            if self.language == "en":
                story.append(Paragraph("Recommendations", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("改进建议", self.styles['SectionTitle']))

            recs = team_data['recommendations']
            if isinstance(recs, list):
                for rec in recs:
                    story.append(Paragraph(f"• {rec}", self.styles['BodyText']))
            else:
                story.append(Paragraph(str(recs), self.styles['BodyText']))

        return story

    def _build_risk_section(self, im_data: Dict[str, Any]) -> List:
        """构建风险评估章节"""
        story = []

        if self.language == "en":
            story.append(Paragraph("5. Risk Evaluation", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("5. 风险评估", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        risks = im_data.get('risks', [])
        if isinstance(risks, list):
            for risk in risks:
                if isinstance(risk, dict):
                    risk_name = risk.get('name', 'Unknown Risk')
                    risk_level = risk.get('level', 'Unknown')
                    risk_desc = risk.get('description', '')

                    story.append(Paragraph(f"<b>{risk_name}</b> ({risk_level})", self.styles['SectionTitle']))
                    if risk_desc:
                        story.append(Paragraph(risk_desc, self.styles['BodyText']))
                    story.append(Spacer(1, 0.1*inch))
                else:
                    story.append(Paragraph(f"• {risk}", self.styles['BodyText']))
        else:
            story.append(Paragraph(str(risks), self.styles['BodyText']))

        return story

    def _build_conclusion(self, im_data: Dict[str, Any]) -> List:
        """构建结论章节"""
        story = []

        if self.language == "en":
            story.append(Paragraph("6. Conclusion and Recommendations", self.styles['ChapterTitle']))
        else:
            story.append(Paragraph("6. 结论与建议", self.styles['ChapterTitle']))

        story.append(Spacer(1, 0.2*inch))

        # 最终建议
        if im_data.get('final_recommendation'):
            if self.language == "en":
                story.append(Paragraph("Final Recommendation", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("最终建议", self.styles['SectionTitle']))

            story.append(Paragraph(str(im_data['final_recommendation']), self.styles['BodyText']))
            story.append(Spacer(1, 0.15*inch))

        # 下一步行动
        if im_data.get('next_steps'):
            if self.language == "en":
                story.append(Paragraph("Next Steps", self.styles['SectionTitle']))
            else:
                story.append(Paragraph("下一步行动", self.styles['SectionTitle']))

            next_steps = im_data['next_steps']
            if isinstance(next_steps, list):
                for step in next_steps:
                    story.append(Paragraph(f"• {step}", self.styles['BodyText']))
            else:
                story.append(Paragraph(str(next_steps), self.styles['BodyText']))

        # 免责声明
        story.append(Spacer(1, 0.3*inch))
        if self.language == "en":
            disclaimer = ("This report is generated by AI and should be used for reference only. "
                        "Please conduct thorough due diligence before making investment decisions.")
        else:
            disclaimer = "本报告由AI生成，仅供参考。投资决策前请进行全面的尽职调查。"

        story.append(Paragraph(f"<i>{disclaimer}</i>", self.styles['BodyText']))

        return story


# 便捷函数
def generate_pdf_report(
    report_data: Dict[str, Any],
    output_path: str,
    language: str = "zh"
) -> str:
    """
    生成PDF报告的便捷函数

    Args:
        report_data: 报告数据
        output_path: 输出文件路径
        language: 语言设置

    Returns:
        生成的PDF文件路径
    """
    generator = PDFReportGenerator(language=language)
    return generator.generate_report(report_data, output_path)
