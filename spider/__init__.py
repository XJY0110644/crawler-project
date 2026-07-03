"""
spider 包 — 共享的网络请求+反爬模块

所有网站共用同一个 spider 模块。
换目标站不需要改这里。
"""

from .base_spider import fetch_page, create_session, random_ua, build_headers

__all__ = ["fetch_page", "create_session", "random_ua", "build_headers"]
