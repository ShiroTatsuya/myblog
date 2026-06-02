#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 GitHub Pages 子路径下图片加载不出来的问题。

原因：站点部署在 https://用户名.github.io/myblog/ 这个子路径下，
但文章里的图片引用是 /images/... （从域名根算起），缺了 /myblog/，
导致线上找不到图。本脚本把所有图片引用从 /images/ 改成 /myblog/images/。

只改 Markdown 图片引用 ![](/images/...)，不动普通链接和正文文字。
原地修改 content/posts 下的 .md 文件，跑前建议先 git commit 一次存档。
"""

import os

# ============ 改这里 ============
POSTS_DIR = r"C:\Users\ShiroX\myblog\content\posts"
PREFIX = "/myblog"   # 你的 baseURL 子路径；若将来换成自定义域名（根路径），把这里改成 ""
# ===============================

OLD = "](/images/"
NEW = "](" + PREFIX + "/images/"


def main():
    changed = 0
    for dp, _, files in os.walk(POSTS_DIR):
        for fn in files:
            if not fn.lower().endswith(".md"):
                continue
            p = os.path.join(dp, fn)
            with open(p, "r", encoding="utf-8") as f:
                s = f.read()
            # 避免重复执行时把 /myblog/myblog/ 叠加：先跳过已修过的
            if NEW in s and OLD not in s.replace(NEW, ""):
                continue
            new = s.replace(OLD, NEW)
            if new != s:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new)
                changed += 1
    print(f"完成：修改了 {changed} 个文件，图片引用已加上 {PREFIX} 前缀。")


if __name__ == "__main__":
    main()
