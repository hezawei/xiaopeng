# models.py
# 从api_agents.py中分离出数据模型定义

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator

# 主题类型定义
class TopicTypes:
    """主题类型定义"""
    API_DOCS_FETCHER = "api_docs_fetcher"
    API_ANALYZER = "api_analyzer"
    TEST_CASE_DESIGNER = "test_case_designer"
    TEST_GENERATOR = "test_generator"
    TEST_EXECUTOR = "test_executor"
    TEST_RESULT_ANALYZER = "test_result_analyzer"
    TEST_REPORT_ENHANCER = "test_report_enhancer"
    TEST_RESULT = "test_result"

# API文档输入参数模型
class APIDocsInput(BaseModel):
    """API文档输入参数模型"""
    api_docs_url: str = Field(..., description="OpenAPI文档的URL")
    base_url: str = Field(..., description="API的基础URL")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    api_doc_content: Optional[Dict[str, Any]] = Field(None, description="OpenAPI文档内容")
    test_focus: Optional[str] = Field(None, description="测试重点，如果为None则全面测试所有API端点")
    api_doc_supplement: Optional[str] = Field(None, description="API文档补充说明，用于提供文档中未包含的信息")

    model_config = ConfigDict(
        title="API文档输入",
        json_schema_extra={
            "example": {
                "api_docs_url": "http://example.com/openapi.json",
                "base_url": "http://example.com/api",
                "enable_review": True,
                "user_review": False,
                "use_local_executor": False
            }
        }
    )

# WebSocket消息模型
class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str = Field(..., description="消息类型：log/progress/result/review/error")
    content: Union[str, Dict[str, Any]] = Field(..., description="消息内容")
    source: str = Field(..., description="消息来源")
    timestamp: Optional[str] = Field(None, description="时间戳")
    has_analysis_report: bool = Field(False, description="是否有分析报告")
    has_html_report: bool = Field(False, description="是否有HTML报告")
    has_allure_report: bool = Field(False, description="是否有Allure报告")

    model_config = ConfigDict(
        title="WebSocket消息",
        arbitrary_types_allowed=True,
        json_encoders={
            # 为无法序列化的类型添加自定义编码器
            object: lambda obj: str(obj),
        }
    )

    @field_validator('timestamp', mode='before')
    def set_timestamp(cls, v):
        return v or datetime.now().isoformat()

    def model_dump_json(self, **kwargs) -> str:
        """确保对象可以被json.dumps序列化"""
        try:
            # 首先尝试使用Pydantic的标准方法
            if hasattr(super(), 'model_dump_json'):
                return super().model_dump_json(**kwargs)
            # 手动转为字典再序列化
            data = self.to_dict()
            return json.dumps(data, **kwargs)
        except Exception as e:
            # 确保即使失败也能返回一个有效的JSON字符串
            return json.dumps({
                "type": self.type,
                "content": str(self.content),
                "source": self.source,
                "timestamp": self.timestamp or datetime.now().isoformat()
            }, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """将WebSocketMessage转换为字典"""
        try:
            if hasattr(self, 'model_dump'):
                result = self.model_dump()
                # 确保结果是可序列化的
                json.dumps(result)
                return result
            else:
                # 手动创建字典
                return {
                    "type": self.type,
                    "content": self.content,
                    "source": self.source,
                    "timestamp": self.timestamp or datetime.now().isoformat(),
                    "has_analysis_report": self.has_analysis_report,
                    "has_html_report": self.has_html_report,
                    "has_allure_report": self.has_allure_report
                }
        except (TypeError, ValueError, OverflowError) as e:
            # 失败时返回安全的字典
            return {
                "type": self.type,
                "content": str(self.content),
                "source": self.source,
                "timestamp": self.timestamp or datetime.now().isoformat(),
                "has_analysis_report": self.has_analysis_report,
                "has_html_report": self.has_html_report,
                "has_allure_report": self.has_allure_report
            }

# API分析结果消息类型
class APIAnalysisResult(BaseModel):
    """API分析结果消息类型"""
    api_docs_url: str = Field(..., description="OpenAPI文档的URL")
    base_url: str = Field(..., description="API的基础URL")
    analysis: str = Field(..., description="API分析结果")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    test_focus: Optional[str] = Field(None, description="测试重点，如果为None则全面测试所有API端点")
    api_doc_supplement: Optional[str] = Field(None, description="API文档补充说明，用于提供文档中未包含的信息")
    template_info: Optional[Dict[str, Any]] = Field(None, description="模板生成所需的分析结果")

# 测试生成结果消息类型
class TestGenerationResult(BaseModel):
    """测试生成结果消息类型"""
    test_file_path: str = Field(..., description="测试文件路径")
    base_url: str = Field(..., description="API的基础URL")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    test_params: Optional[Dict[str, Any]] = Field(None, description="测试参数配置")
    test_dir: Optional[str] = Field(None, description="测试目录路径")
    pytest_options: Optional[str] = Field("", description="pytest命令行选项")
    utils_code: str = Field("", description="utils.py文件内容")
    conftest_code: str = Field("", description="conftest.py文件内容")
    test_code: str = Field("", description="测试脚本内容")
    review_notes: Dict[str, List[str]] = Field(default_factory=dict, description="代码审查笔记")
    allure_results_dir: Optional[str] = Field(None, description="Allure结果目录")

# 测试执行输出消息类型
class TestExecutionOutput(BaseModel):
    """测试执行输出消息类型，用于测试执行和分析智能体之间的通信"""
    test_file_path: str = Field(..., description="测试文件路径")
    output: str = Field(..., description="测试执行输出")
    exit_code: int = Field(..., description="测试执行退出码")
    stats: Dict[str, Any] = Field(..., description="测试统计信息")
    report_path: Optional[str] = Field(None, description="HTML报告路径")
    json_report_path: Optional[str] = Field(None, description="JSON报告路径")
    allure_results_dir: Optional[str] = Field(None, description="Allure结果目录")
    report_data: Optional[Dict[str, Any]] = Field(None, description="JSON报告数据")
    test_params: Optional[Dict[str, Any]] = Field(None, description="测试执行参数")

# 测试执行结果消息类型
class TestExecutionResult(BaseModel):
    """测试执行结果消息类型"""
    test_result: Dict[str, Any] = Field(..., description="测试结果")
    test_file_path: str = Field(..., description="测试文件路径")
    analysis: str = Field(..., description="测试结果分析")
    report_url: Optional[str] = Field(None, description="测试报告URL")
    allure_report_url: Optional[str] = Field(None, description="Allure测试报告URL")
    allure_results_dir: Optional[str] = Field(None, description="Allure结果目录")
    test_params: Optional[Dict[str, Any]] = Field(None, description="测试执行参数")

# 测试用例设计结果消息类型
class TestCaseDesignResult(BaseModel):
    """测试用例设计结果消息类型"""
    api_docs_url: str = Field(..., description="OpenAPI文档的URL")
    base_url: str = Field(..., description="API的基础URL")
    test_cases: str = Field(..., description="设计的测试用例")
    api_analysis: str = Field(..., description="API分析结果")
    enable_review: bool = Field(True, description="是否启用测试用例评审")
    user_review: bool = Field(False, description="是否需要用户参与评审")
    use_local_executor: bool = Field(False, description="是否使用本地代码执行器")
    test_focus: Optional[str] = Field(None, description="测试重点，如果为None则全面测试所有API端点")
    api_doc_supplement: Optional[str] = Field(None, description="API文档补充说明，用于提供文档中未包含的信息")
    template_info: Optional[Dict[str, Any]] = Field(None, description="模板生成所需的分析结果")
    test_case_metadata: Optional[Dict[str, Any]] = Field(None, description="测试用例元数据，如用例数量、覆盖率等") 