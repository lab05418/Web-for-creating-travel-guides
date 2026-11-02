"""小红书抓取错误分类。

把「鉴权失效」「限流」「网络」「签名」「解析」分开，便于重试、熔断和告警；
不要把所有异常都包装成同一条“抓取失败”。
"""

from __future__ import annotations


class XhsError(Exception):
    """小红书抓取基础异常。"""


class XhsAuthError(XhsError):
    """Cookie 失效、登录墙、风控拦截。"""


class XhsRateLimitError(XhsError):
    """429 或平台频率限制。"""


class XhsNetworkError(XhsError):
    """超时、连接失败、DNS 等。"""


class XhsSignatureError(XhsError):
    """Node 签名运行时/JS 执行异常。"""


class XhsParseError(XhsError):
    """响应不是预期 JSON/HTML 结构变化。"""


class XhsContentError(XhsError):
    """请求成功但没有可用内容。"""
