"""
Chart Generator Module
图表生成模块

Generates various charts for investment analysis reports:
- Financial charts (revenue, profit, health metrics)
- Market analysis charts (market share, growth, competitive landscape, TAM)
- Team and risk visualizations (org chart, risk matrix, radar charts)

Uses matplotlib and seaborn for professional data visualization.
使用matplotlib和seaborn生成专业的数据可视化图表。
"""

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server-side generation

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import numpy as np
from typing import Dict, Any, List, Union
import io
import logging

# Type for output path - can be a file path string or a BytesIO object
OutputPath = Union[str, io.BytesIO]

logger = logging.getLogger(__name__)

# Set style for professional charts
sns.set_style("whitegrid")

# Configure fonts for Chinese support
# Search for available Chinese fonts in the system
def _find_chinese_font():
    """Find available Chinese font in the system"""
    # Priority list of Chinese fonts
    # Note: Noto Sans CJK JP/SC/TC all support CJK characters
    chinese_fonts = [
        'Noto Sans CJK JP',      # Common on Linux containers (supports all CJK)
        'Noto Sans CJK SC',      # Linux (apt-get install fonts-noto-cjk)
        'Noto Sans CJK TC',
        'Noto Serif CJK JP',     # Serif variant
        'Noto Serif CJK SC',
        'Noto Sans SC',
        'Noto Sans TC',
        'WenQuanYi Micro Hei',   # Linux alternative
        'WenQuanYi Zen Hei',
        'Source Han Sans SC',    # Adobe Source Han
        'Source Han Sans CN',
        'PingFang SC',           # macOS
        'Heiti SC',
        'Heiti TC',
        'Microsoft YaHei',       # Windows
        'SimHei',
        'SimSun',
        'Arial Unicode MS',
        'DejaVu Sans',           # Fallback
    ]

    # Get all available font names
    available_fonts = set([f.name for f in fm.fontManager.ttflist])
    logger.info(f"Available fonts: {len(available_fonts)} total")

    # Log CJK fonts found
    cjk_available = [f for f in available_fonts if 'CJK' in f or 'Noto' in f]
    if cjk_available:
        logger.info(f"CJK fonts found: {cjk_available}")

    for font in chinese_fonts:
        if font in available_fonts:
            logger.info(f"Using Chinese font: {font}")
            return font

    # If no Chinese font found, log warning
    logger.warning("No Chinese font found, charts may not display Chinese characters correctly")
    return 'DejaVu Sans'

# Find and set Chinese font
_chinese_font = _find_chinese_font()
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = [_chinese_font, 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # Ensure minus signs are shown correctly
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3


class ChartGenerator:
    """
    Chart Generator for Investment Analysis Reports
    投资分析报告图表生成器
    """

    def __init__(self, language: str = "zh"):
        """
        Initialize chart generator

        Args:
            language: Language setting ("zh" or "en")
        """
        self.language = language
        self.color_palette = {
            'primary': '#6366F1',  # Indigo
            'success': '#10B981',  # Green
            'warning': '#F59E0B',  # Amber
            'danger': '#EF4444',   # Red
            'info': '#3B82F6',     # Blue
            'neutral': '#6B7280',  # Gray
        }

    # ==================== FINANCIAL CHARTS ====================

    def _save_figure(self, fig, output_path: OutputPath) -> OutputPath:
        """Save figure to file or BytesIO"""
        plt.tight_layout()
        if isinstance(output_path, io.BytesIO):
            plt.savefig(output_path, format='png', dpi=150, bbox_inches='tight')
        else:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        return output_path

    def generate_revenue_chart(
        self,
        financial_data: Dict[str, Any],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate revenue trend chart
        生成收入趋势图

        Args:
            financial_data: Financial data with revenue over time
            output_path: Path to save the chart (str or BytesIO)

        Returns:
            Path to the generated chart or BytesIO
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Extract revenue data
        years = financial_data.get('years', [2021, 2022, 2023])
        revenue = financial_data.get('revenue', [1000000, 1500000, 2200000])

        # Plot
        ax.plot(years, revenue, marker='o', linewidth=3, markersize=10, color=self.color_palette['primary'])
        ax.fill_between(years, revenue, alpha=0.2, color=self.color_palette['primary'])

        # Labels and title
        title = "Revenue Trend" if self.language == "en" else "收入趋势"
        ylabel = "Revenue (¥)" if self.language == "en" else "收入 (¥)"
        xlabel = "Year" if self.language == "en" else "年份"

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_xlabel(xlabel, fontsize=12)

        # Format y-axis to show millions
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x/1e6:.1f}M'))

        # Add value labels on points
        for i, (year, rev) in enumerate(zip(years, revenue)):
            ax.annotate(f'¥{rev/1e6:.1f}M',
                       xy=(year, rev),
                       xytext=(0, 10),
                       textcoords='offset points',
                       ha='center',
                       fontsize=10,
                       fontweight='bold')

        return self._save_figure(fig, output_path)

    def generate_profit_chart(
        self,
        financial_data: Dict[str, Any],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate profit margin chart
        生成利润率图表

        Args:
            financial_data: Financial data with profit margins
            output_path: Path to save the chart

        Returns:
            Path to the generated chart
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Extract profit data
        years = financial_data.get('years', [2021, 2022, 2023])
        gross_margin = financial_data.get('gross_margin', [0.45, 0.52, 0.58])
        net_margin = financial_data.get('net_margin', [0.15, 0.22, 0.28])

        x = np.arange(len(years))
        width = 0.35

        # Create bars
        bars1 = ax.bar(x - width/2, gross_margin, width, label='Gross Margin' if self.language == 'en' else '毛利率',
                       color=self.color_palette['success'])
        bars2 = ax.bar(x + width/2, net_margin, width, label='Net Margin' if self.language == 'en' else '净利率',
                       color=self.color_palette['info'])

        # Labels and title
        title = "Profit Margin Trends" if self.language == "en" else "利润率趋势"
        ylabel = "Margin (%)" if self.language == "en" else "利润率 (%)"
        xlabel = "Year" if self.language == "en" else "年份"

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(years)
        ax.legend()

        # Format y-axis as percentage
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*100:.0f}%'))

        # Add value labels on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height*100:.1f}%',
                       ha='center', va='bottom', fontsize=9)

        return self._save_figure(fig, output_path)

    def generate_financial_health_score(
        self,
        health_metrics: Dict[str, float],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate financial health scorecard
        生成财务健康度评分卡

        Args:
            health_metrics: Dict with metrics like liquidity, solvency, profitability, efficiency
            output_path: Path to save the chart

        Returns:
            Path to the generated chart
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # Extract metrics
        categories = []
        scores = []

        metric_labels = {
            'liquidity': 'Liquidity' if self.language == 'en' else '流动性',
            'solvency': 'Solvency' if self.language == 'en' else '偿债能力',
            'profitability': 'Profitability' if self.language == 'en' else '盈利能力',
            'efficiency': 'Efficiency' if self.language == 'en' else '运营效率',
            'growth': 'Growth' if self.language == 'en' else '增长性'
        }

        for key, label in metric_labels.items():
            if key in health_metrics:
                categories.append(label)
                scores.append(health_metrics[key] * 100)  # Convert to 0-100 scale

        # Create horizontal bar chart
        colors = [self.color_palette['success'] if s >= 70 else
                 self.color_palette['warning'] if s >= 50 else
                 self.color_palette['danger'] for s in scores]

        bars = ax.barh(categories, scores, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

        # Add value labels
        for i, (bar, score) in enumerate(zip(bars, scores)):
            ax.text(score + 2, i, f'{score:.1f}', va='center', fontsize=11, fontweight='bold')

        # Labels and title
        title = "Financial Health Scorecard" if self.language == "en" else "财务健康度评分"
        xlabel = "Score (0-100)" if self.language == "en" else "评分 (0-100)"

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_xlim(0, 110)

        # Add reference lines
        ax.axvline(x=50, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=70, color='gray', linestyle='--', alpha=0.5, linewidth=1)

        return self._save_figure(fig, output_path)

    # ==================== MARKET ANALYSIS CHARTS ====================

    def generate_market_share_chart(
        self,
        market_data: Dict[str, Any],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate market share pie chart
        生成市场份额饼图

        Args:
            market_data: Market data with company shares
            output_path: Path to save the chart

        Returns:
            Path to the generated chart
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # Extract data
        companies = market_data.get('companies', ['Target Company', 'Competitor A', 'Competitor B', 'Others'])
        shares = market_data.get('shares', [15, 25, 20, 40])

        # Create pie chart
        colors = [self.color_palette['primary'], self.color_palette['info'],
                 self.color_palette['warning'], self.color_palette['neutral']]

        wedges, texts, autotexts = ax.pie(shares, labels=companies, autopct='%1.1f%%',
                                          colors=colors, startangle=90,
                                          textprops={'fontsize': 11})

        # Make percentage text bold
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
            autotext.set_fontsize(12)

        # Title
        title = "Market Share Distribution" if self.language == "en" else "市场份额分布"
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

        return self._save_figure(fig, output_path)

    def generate_market_growth_chart(
        self,
        market_data: Dict[str, Any],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate market growth trend chart
        生成市场增长趋势图

        Args:
            market_data: Market data with growth over time
            output_path: Path to save the chart

        Returns:
            Path to the generated chart
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        # Extract data
        years = market_data.get('years', [2019, 2020, 2021, 2022, 2023])
        market_size = market_data.get('market_size', [500, 650, 850, 1100, 1400])  # in millions
        growth_rate = market_data.get('growth_rate', [None, 30, 31, 29, 27])  # YoY %

        # Create dual-axis chart
        color1 = self.color_palette['primary']
        color2 = self.color_palette['success']

        # Market size line
        ax.plot(years, market_size, marker='o', linewidth=3, markersize=10,
               color=color1, label='Market Size' if self.language == 'en' else '市场规模')
        ax.fill_between(years, market_size, alpha=0.2, color=color1)

        # Growth rate line (secondary axis)
        ax2 = ax.twinx()
        ax2.plot(years[1:], growth_rate[1:], marker='s', linewidth=2, markersize=8,
                color=color2, linestyle='--', label='Growth Rate' if self.language == 'en' else '增长率')

        # Labels and title
        title = "Market Growth Trend" if self.language == "en" else "市场增长趋势"
        ylabel1 = "Market Size (¥M)" if self.language == "en" else "市场规模 (¥百万)"
        ylabel2 = "Growth Rate (%)" if self.language == "en" else "增长率 (%)"
        xlabel = "Year" if self.language == "en" else "年份"

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel(ylabel1, fontsize=12, color=color1)
        ax.set_xlabel(xlabel, fontsize=12)
        ax2.set_ylabel(ylabel2, fontsize=12, color=color2)

        # Color tick labels
        ax.tick_params(axis='y', labelcolor=color1)
        ax2.tick_params(axis='y', labelcolor=color2)

        # Legends
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        return self._save_figure(fig, output_path)

    # ==================== TEAM & RISK VISUALIZATIONS ====================

    def generate_risk_matrix(
        self,
        risks: List[Dict[str, Any]],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate risk assessment matrix (probability vs impact)
        生成风险评估矩阵图

        Args:
            risks: List of risks with probability and impact scores
            output_path: Path to save the chart

        Returns:
            Path to the generated chart
        """
        fig, ax = plt.subplots(figsize=(10, 8))

        # Extract risk data
        probabilities = []
        impacts = []
        labels = []

        for risk in risks:
            prob = risk.get('probability', 0.5)  # 0-1 scale
            impact = risk.get('impact', 0.5)     # 0-1 scale
            name = risk.get('name', 'Unknown Risk')

            probabilities.append(prob * 100)  # Convert to 0-100
            impacts.append(impact * 100)
            labels.append(name)

        # Determine colors based on risk level (prob * impact)
        colors = []
        for p, i in zip(probabilities, impacts):
            risk_score = (p * i) / 100  # 0-100 scale
            if risk_score >= 70:
                colors.append(self.color_palette['danger'])
            elif risk_score >= 40:
                colors.append(self.color_palette['warning'])
            else:
                colors.append(self.color_palette['success'])

        # Scatter plot
        scatter = ax.scatter(probabilities, impacts, s=500, c=colors, alpha=0.6, edgecolors='black', linewidth=2)

        # Add labels for each risk
        for i, label in enumerate(labels):
            ax.annotate(label, (probabilities[i], impacts[i]),
                       ha='center', va='center', fontsize=9, fontweight='bold')

        # Add quadrant lines
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=50, color='gray', linestyle='--', alpha=0.5)

        # Add quadrant labels
        quad_labels = {
            'en': {
                'low': 'Low Risk', 'medium': 'Medium Risk',
                'high_prob': 'Monitor', 'high_impact': 'Manage'
            },
            'zh': {
                'low': '低风险', 'medium': '中等风险',
                'high_prob': '密切关注', 'high_impact': '重点管理'
            }
        }
        lang_labels = quad_labels['en'] if self.language == 'en' else quad_labels['zh']

        # Labels and title
        title = "Risk Assessment Matrix" if self.language == "en" else "风险评估矩阵"
        xlabel = "Probability (%)" if self.language == "en" else "发生概率 (%)"
        ylabel = "Impact (%)" if self.language == "en" else "影响程度 (%)"

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_xlim(0, 105)
        ax.set_ylim(0, 105)

        return self._save_figure(fig, output_path)

    def generate_team_radar_chart(
        self,
        team_scores: Dict[str, float],
        output_path: OutputPath
    ) -> OutputPath:
        """
        Generate team capability radar chart
        生成团队能力雷达图

        Args:
            team_scores: Dict with scores for different capabilities
            output_path: Path to save the chart

        Returns:
            Path to the generated chart
        """
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        # Labels mapping
        capability_labels = {
            'technical': 'Technical' if self.language == 'en' else '技术能力',
            'market': 'Market' if self.language == 'en' else '市场能力',
            'leadership': 'Leadership' if self.language == 'en' else '领导力',
            'execution': 'Execution' if self.language == 'en' else '执行力',
            'finance': 'Finance' if self.language == 'en' else '财务管理',
            'innovation': 'Innovation' if self.language == 'en' else '创新能力'
        }

        # Extract data
        categories = []
        scores = []

        for key, label in capability_labels.items():
            if key in team_scores:
                categories.append(label)
                scores.append(team_scores[key] * 10)  # Convert to 0-10 scale

        # Number of variables
        num_vars = len(categories)

        # Compute angle for each axis
        angles = [n / float(num_vars) * 2 * np.pi for n in range(num_vars)]
        scores += scores[:1]  # Complete the circle
        angles += angles[:1]

        # Plot
        ax.plot(angles, scores, 'o-', linewidth=2, color=self.color_palette['primary'])
        ax.fill(angles, scores, alpha=0.25, color=self.color_palette['primary'])

        # Fix axis to go in the right order
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, size=11)

        # Set y-axis limit
        ax.set_ylim(0, 10)

        # Title
        title = "Team Capability Assessment" if self.language == "en" else "团队能力评估"
        ax.set_title(title, size=16, fontweight='bold', pad=30)

        # Add gridlines
        ax.grid(True, linestyle='--', alpha=0.7)

        return self._save_figure(fig, output_path)


def generate_chart_for_report(
    chart_type: str,
    data: Dict[str, Any],
    output_path: str,
    language: str = "zh"
) -> str:
    """
    Convenience function to generate a chart

    Args:
        chart_type: Type of chart to generate
        data: Chart data
        output_path: Path to save the chart
        language: Language setting

    Returns:
        Path to the generated chart
    """
    generator = ChartGenerator(language=language)

    chart_methods = {
        'revenue': generator.generate_revenue_chart,
        'profit': generator.generate_profit_chart,
        'financial_health': generator.generate_financial_health_score,
        'market_share': generator.generate_market_share_chart,
        'market_growth': generator.generate_market_growth_chart,
        'risk_matrix': generator.generate_risk_matrix,
        'team_radar': generator.generate_team_radar_chart
    }

    if chart_type not in chart_methods:
        raise ValueError(f"Unknown chart type: {chart_type}")

    return chart_methods[chart_type](data, output_path)
