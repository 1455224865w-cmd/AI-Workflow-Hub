"""中英文切换。默认中文，已有调用不传语言时行为不变。"""

from __future__ import annotations

import os

import re
from contextvars import ContextVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

current_locale: ContextVar[str] = ContextVar("locale", default="zh")
LOCALES = ("zh", "en")
TEXT_FIELDS = {
    "name", "summary", "message", "detail", "reason", "impact", "direction",
    "risk", "verification", "answer", "error", "prompt",
}

def negotiate(header: str | None, query: str | None = None) -> str:
    if query in LOCALES:
        return query
    if header:
        for part in header.split(","):
            token = part.split(";", 1)[0].strip().lower().replace("_", "-")
            if token.startswith("en"):
                return "en"
            if token.startswith("zh"):
                return "zh"
    fallback = os.environ.get("APP_LOCALE", "zh").strip().lower()
    return fallback if fallback in LOCALES else "zh"


def localize_error(message: str, locale: str) -> str:
    if locale != "en":
        return message
    if message in EN:
        return EN[message]
    for pattern, template in PATTERNS:
        matched = pattern.fullmatch(message)
        if matched:
            return template.format(*matched.groups())
    return message


def text(key: str, locale: str) -> str:
    table = TEXT.get(locale) or TEXT["zh"]
    return table.get(key) or TEXT["zh"][key]


def translate_payload(value, locale: str):
    if locale != "en":
        return value
    if isinstance(value, dict):
        translated = {}
        for key, item in value.items():
            if key == "suggestions" and isinstance(item, list):
                translated[key] = [
                    localize_error(piece, "en") if isinstance(piece, str) else translate_payload(piece, "en")
                    for piece in item
                ]
            elif key in TEXT_FIELDS and isinstance(item, str):
                translated[key] = localize_error(item, "en")
            else:
                translated[key] = translate_payload(item, "en")
        return translated
    if isinstance(value, list):
        return [translate_payload(item, "en") for item in value]
    return value


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def bind_locale(request: Request, call_next):
        token = current_locale.set(negotiate(request.headers.get("accept-language"), request.query_params.get("lang")))
        try:
            return await call_next(request)
        finally:
            current_locale.reset(token)

    @app.exception_handler(HTTPException)
    async def translate_http(request: Request, exc: HTTPException):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        detail = exc.detail
        if isinstance(detail, str):
            detail = localize_error(detail, locale)
        return JSONResponse(status_code=exc.status_code, content={"detail": detail})

    @app.get("/api/meta")
    def meta(request: Request):
        locale = negotiate(request.headers.get("accept-language"), request.query_params.get("lang"))
        return {
            "locale": locale,
            "locales": list(LOCALES),
            "mcp": "/mcp",
            "springAi": "streamable-http",
            "message": text("meta.ready", locale),
        }


EN = {
    "未知工具": "Unknown tool",
    "工作流不能为空": "A workflow is required",
    "工作流超过长度限制": "The workflow exceeds the length limit",
    "工作流必须是映射": "A workflow must be a mapping",
    "只接受 version: 1": "Only version: 1 is accepted",
    "工作流需要名称": "A workflow needs a name",
    "节点数量必须在 1 到 100": "The node count must be from 1 to 100",
    "节点 id 必须是非空字符串": "A node id must be a non-empty string",
    "重试次数必须在 0 到 5": "Retry count must be from 0 to 5",
    "timeout_seconds 必须大于 0 且不超过 300": "timeout_seconds must be greater than 0 and at most 300",
    "节点 id 不能重复": "Node ids must be unique",
    "inputs 必须是列表": "inputs must be a list",
    "输入名称必须是合法标识符": "An input name must be an identifier",
    "输入名称不能重复": "Input names must be unique",
    "必须有且只有一个 start": "There must be exactly one start",
    "至少要有一个 end": "At least one end is required",
    "边引用了不存在的节点": "An edge references a missing node",
    "边的 when 只能是 true 或 false": "An edge when value must be true or false",
    "工作流不允许循环": "Cycles are not allowed",
    "HTTP 节点只允许 http 或 https": "HTTP nodes allow only http or https",
    "无法确认目标地址，已拒绝请求": "The target address could not be confirmed, so the request was refused",
    "目标没有地址，已拒绝请求": "The target has no address, so the request was refused",
    "HTTP 节点拒绝访问内网、本机和链路本地地址": "HTTP nodes refuse private, loopback, and link-local addresses",
    "上下文超过 16384 字节": "Context exceeds 16384 bytes",
    "恢复记录里有未知节点": "The resume record contains an unknown node",
    "执行步数超过上限": "The execution exceeded the step limit",
    "等待时间不能为负": "A delay cannot be negative",
    "节点超时": "The node timed out",
    "script 节点只允许 action: set，不执行任意代码": "A script node allows only action: set and does not run arbitrary code",
    "变量名不合法": "The variable name is invalid",
    "没有配置模型提供方，已拒绝发送请求": "No model provider is configured, so the request was refused",
    "没有配置 HTTP 传输，拒绝直接访问网络": "No HTTP transport is configured, so the network is not contacted",
    "不支持的表达式": "Unsupported expression",
    "字符串没有结束": "The string is not closed",
    "无法计算表达式": "The expression cannot be evaluated",
    "运行记录不存在": "Run record does not exist",
    "审批被拒绝": "Approval was denied",
    "没有到达 end": "The run did not reach end",
    "空跑只给出顺序，不调用 HTTP、模型或 Shell。": "Dry run returns the order only. It does not call HTTP, a model, or a shell.",
}

PATTERNS = [
    (re.compile(r"未知节点类型 (.+)"), "Unknown node type {0}"),
    (re.compile(r"缺少必填输入 (.+)"), "Missing required input {0}"),
    (re.compile(r"等待审批:(.+)"), "Waiting for approval: {0}"),
    (re.compile(r"未实现的节点 (.+)"), "Node is not implemented: {0}"),
    (re.compile(r"上下文没有变量 (.+)"), "Variable is not in the context: {0}"),
]

TEXT = {
    "zh": {
        "meta.ready": "当前语言是中文。MCP 端点是 /mcp，供 Spring AI Streamable HTTP 客户端连接。",
        "mcp.instructions": "工具只读或只记录，不执行日志命令，不连接生产数据库，也不把推测写成事实。",
        "mcp.invalid": "请求无效",
        "mcp.protocol": "不支持的 MCP 协议版本",
        "mcp.arguments": "工具参数必须是对象",
        "mcp.json": "请求不是 JSON",
        "mcp.method": "不支持的 MCP 方法",
        "tool.dry": "校验并空跑一份工作流。不访问网络，不执行 Shell。",
        "tool.dry.result": "空跑只给出顺序，不调用 HTTP、模型或 Shell。",
    },
    "en": {
        "meta.ready": "The current language is English. The MCP endpoint is /mcp for a Spring AI Streamable HTTP client.",
        "mcp.instructions": "Tools only read or record. They do not run log commands, connect to production databases, or treat inferences as facts.",
        "mcp.invalid": "Invalid request",
        "mcp.protocol": "Unsupported MCP protocol version",
        "mcp.arguments": "Tool arguments must be an object",
        "mcp.json": "Request is not JSON",
        "mcp.method": "Unsupported MCP method",
        "tool.dry": "Validate a workflow and return its order. It does not use the network or execute a shell.",
        "tool.dry.result": "Dry run returns the order only. It does not call HTTP, a model, or a shell.",
    },
}
