from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PerformanceMetric(BaseModel):
    """性能指标模型"""
    name: str = Field(..., description="指标名称")
    value: str = Field(..., description="当前值")
    benchmark: str = Field(..., description="基准值")
    status: str = Field(..., description="状态：良好、一般、差")
    percentOfBenchmark: Optional[float] = Field(None, description="与基准值的百分比")


class PerformanceBottleneck(BaseModel):
    """性能瓶颈模型"""
    id: str = Field(..., description="唯一标识")
    type: str = Field(..., description="瓶颈类型")
    description: str = Field(..., description="问题描述")
    impact: str = Field(..., description="影响")
    location: str = Field(..., description="问题位置")
    severity: str = Field(..., description="严重程度：严重、中等、轻微")


class PerformanceRecommendation(BaseModel):
    """性能优化建议模型"""
    id: str = Field(..., description="唯一标识")
    title: str = Field(..., description="建议标题")
    description: str = Field(..., description="建议描述")
    implementation: str = Field(..., description="实施方法")
    impact: str = Field(..., description="预期影响")
    impact_level: str = Field(..., description="影响等级：高、中、低")


class PerformanceSummary(BaseModel):
    """性能总结模型"""
    title: str = Field("性能分析总结", description="总结标题")
    timestamp: str = Field(..., description="分析时间戳")
    overallScore: int = Field(..., description="总体评分(0-100)")
    content: str = Field(..., description="总结内容")
    highlights: List[str] = Field(default=[], description="关键发现点")


class PerformanceMetricsData(BaseModel):
    """性能指标数据集合"""
    title: str = Field("关键性能指标", description="指标标题")
    data: List[PerformanceMetric] = Field(default=[], description="指标数据列表")


class PerformanceChart(BaseModel):
    """性能图表数据"""
    title: str = Field(..., description="图表标题")
    type: str = Field(..., description="图表类型：line, bar, pie等")
    data: Dict[str, Any] = Field(..., description="图表数据")


class PerformanceReport(BaseModel):
    """性能报告上传信息模型"""
    id: str = Field(..., description="报告唯一标识")
    filename: str = Field(..., description="原始文件名")
    upload_time: str = Field(..., description="上传时间")
    file_size: int = Field(..., description="文件大小(字节)")
    file_type: str = Field(..., description="文件类型")
    analysis_status: str = Field("pending", description="分析状态：pending, processing, completed, failed")


class PerformanceAnalysisResult(BaseModel):
    """性能分析结果模型"""
    summary: PerformanceSummary = Field(..., description="性能概览")
    metrics: PerformanceMetricsData = Field(..., description="性能指标数据")
    bottlenecks: List[PerformanceBottleneck] = Field(default=[], description="性能瓶颈列表")
    recommendations: List[PerformanceRecommendation] = Field(default=[], description="优化建议列表")
    charts: List[PerformanceChart] = Field(default=[], description="可视化图表数据") 