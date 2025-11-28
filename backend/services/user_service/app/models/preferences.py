# backend/services/user_service/app/models/preferences.py
"""
Institution Investment Preferences Models
机构投资偏好数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime


class InvestmentRange(BaseModel):
    """投资金额区间"""
    min_amount: float = Field(..., description="最小投资金额（万元）")
    max_amount: float = Field(..., description="最大投资金额（万元）")
    currency: str = Field(default="CNY", description="货币单位")


class InstitutionPreference(BaseModel):
    """机构投资偏好"""
    user_id: str = Field(..., description="用户/机构ID")
    
    # 投资主题
    investment_thesis: List[str] = Field(
        default_factory=list,
        description="投资主题，如 ['AI', 'SaaS', '企业服务']"
    )
    
    # 偏好阶段
    preferred_stages: List[str] = Field(
        default_factory=list,
        description="偏好融资阶段，如 ['Seed', 'Pre-A', 'A']"
    )
    
    # 关注行业
    focus_industries: List[str] = Field(
        default_factory=list,
        description="关注行业，如 ['企业软件', '医疗健康', '新能源']"
    )
    
    # 排除行业
    excluded_industries: List[str] = Field(
        default_factory=list,
        description="排除的行业，如 ['区块链', '游戏', '房地产']"
    )
    
    # 地域偏好
    geography_preference: List[str] = Field(
        default_factory=list,
        description="地域偏好，如 ['北京', '上海', '深圳', '杭州']"
    )
    
    # 投资金额区间
    investment_range: Optional[InvestmentRange] = Field(
        None,
        description="单笔投资金额区间"
    )
    
    # 其他偏好
    min_team_size: Optional[int] = Field(None, description="最小团队规模")
    require_revenue: Optional[bool] = Field(None, description="是否要求已有收入")
    require_product: Optional[bool] = Field(None, description="是否要求产品已上线")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "institution_001",
                "investment_thesis": ["AI", "SaaS", "企业服务"],
                "preferred_stages": ["Pre-A", "A"],
                "focus_industries": ["企业软件", "人工智能"],
                "excluded_industries": ["区块链", "游戏"],
                "geography_preference": ["北京", "上海", "深圳"],
                "investment_range": {
                    "min_amount": 1000,
                    "max_amount": 5000,
                    "currency": "CNY"
                },
                "min_team_size": 5,
                "require_revenue": False,
                "require_product": True
            }
        }


class PreferenceCreateRequest(BaseModel):
    """创建偏好请求"""
    user_id: str
    investment_thesis: List[str] = []
    preferred_stages: List[str] = []
    focus_industries: List[str] = []
    excluded_industries: List[str] = []
    geography_preference: List[str] = []
    investment_range: Optional[InvestmentRange] = None
    min_team_size: Optional[int] = None
    require_revenue: Optional[bool] = None
    require_product: Optional[bool] = None


class PreferenceUpdateRequest(BaseModel):
    """更新偏好请求"""
    investment_thesis: Optional[List[str]] = None
    preferred_stages: Optional[List[str]] = None
    focus_industries: Optional[List[str]] = None
    excluded_industries: Optional[List[str]] = None
    geography_preference: Optional[List[str]] = None
    investment_range: Optional[InvestmentRange] = None
    min_team_size: Optional[int] = None
    require_revenue: Optional[bool] = None
    require_product: Optional[bool] = None


class PreferenceResponse(BaseModel):
    """偏好响应"""
    success: bool
    message: str
    preference: Optional[InstitutionPreference] = None
