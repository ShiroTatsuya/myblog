#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian -> Hugo 迁移脚本（递归 + 文件夹分区版）

相比上一版的变化：
  * 递归扫描每个来源下的所有子文件夹（之前只扫顶层，会漏掉子目录里的笔记）
  * 把 Obsidian 的文件夹层级原样映射成 Hugo 的 section 子目录
    例如 Knowledge\武器资料\某笔记.md  ->  content/posts/knowledge/武器资料/某笔记.md
  * 图片改为“全盘索引”：先登记来源下所有 Images 文件夹里的图，再按文件名匹配，
    不管图在主目录还是子目录的 Images 里都能找到
  * 给每个分类目录自动生成 _index.md，PaperMod 才会把它当成独立分类页

【重要】CLEAR_POSTS / CLEAR_IMAGES 默认开着，会先清空 content/posts 和
static/images 再重新生成。跑之前请先备份整个 myblog 文件夹，或先 git commit 一次存档。
原始 Obsidian 文件不会被改动。
"""

import os
import re
import shutil
import datetime
import urllib.parse

# ===================== 改这里 =====================
HUGO_PROJECT = r"C:\Users\ShiroX\myblog"

# 每个来源：label 是分类名（会出现在 URL 里），root 是该来源在 Obsidian 里的根文件夹
SOURCES = [
    {"label": "knowledge",
     "root": r"E:\Obsidian-vault\obsidian-vault\02_LIBRARY\R_Resources\Knowledge"},
    {"label": "methods",
     "root": r"E:\Obsidian-vault\obsidian-vault\02_LIBRARY\A_Areas\TRPG\Methods"},
]

DATE_SOURCE  = "mtime"   # "mtime" 修改时间 / "ctime" 创建时间
CLEAR_POSTS  = True      # 重跑前清空 content/posts
CLEAR_IMAGES = True      # 重跑前清空 static/images
# =================================================

POSTS_DIR  = os.path.join(HUGO_PROJECT, "content", "posts")
STATIC_IMG = os.path.join(HUGO_PROJECT, "static", "images")
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"}
EMBED_RE = re.compile(r'!\[\[([^\]\|]+?)(?:\|[^\]]*)?\]\]')          # ![[img.png]] / ![[img.png|300]]
LINK_RE  = re.compile(r'(?<!\!)\[\[([^\]\|]+?)(?:\|([^\]]*))?\]\]')  # [[note]] / [[note|alias]]


def yaml_escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def get_date(path):
    ts = os.path.getctime(path) if DATE_SOURCE == "ctime" else os.path.getmtime(path)
    dt = datetime.datetime.fromtimestamp(ts).astimezone()  # 附带系统本地时区
    s = dt.strftime("%Y-%m-%dT%H:%M:%S%z")                 # 例 2026-06-02T16:05:39+0800
    return s[:-2] + ":" + s[-2:]                            # -> +08:00（Hugo 最规范格式）


def build_image_index(root):
    """递归登记 root 下所有图片，键为文件名（含一个小写兜底键）。"""
    idx = {}
    for dp, _, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMG_EXT:
                idx.setdefault(f, os.path.join(dp, f))
                idx.setdefault(f.lower(), os.path.join(dp, f))
    return idx


def main():
    if CLEAR_POSTS and os.path.isdir(POSTS_DIR):
        shutil.rmtree(POSTS_DIR)
    if CLEAR_IMAGES and os.path.isdir(STATIC_IMG):
        shutil.rmtree(STATIC_IMG)
    os.makedirs(POSTS_DIR, exist_ok=True)
    os.makedirs(STATIC_IMG, exist_ok=True)

    total = 0
    missing = []

    for src in SOURCES:
        label, root = src["label"], src["root"]
        if not os.path.isdir(root):
            print(f"[跳过] 找不到目录：{root}")
            continue
        img_index = build_image_index(root)
        out_img_dir = os.path.join(STATIC_IMG, label)
        os.makedirs(out_img_dir, exist_ok=True)

        for dp, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d.lower() != "images"]  # 不把 Images 当内容目录
            for fn in files:
                if not fn.lower().endswith(".md"):
                    continue
                src_path = os.path.join(dp, fn)
                rel = os.path.relpath(dp, root)
                stem = os.path.splitext(fn)[0]

                with open(src_path, "r", encoding="utf-8") as f:
                    body = f.read()

                def repl_embed(m):
                    base = os.path.basename(m.group(1).strip())
                    real = img_index.get(base) or img_index.get(base.lower())
                    if real and os.path.isfile(real):
                        shutil.copy2(real, os.path.join(out_img_dir, base))
                    else:
                        missing.append(f"{os.path.join(label, rel, fn)}：{base}")
                    return "![](" + "/images/" + label + "/" + urllib.parse.quote(base) + ")"

                def repl_link(m):
                    return (m.group(2) if m.group(2) else m.group(1)).strip()

                body = EMBED_RE.sub(repl_embed, body)
                body = LINK_RE.sub(repl_link, body)

                out_dir = os.path.join(POSTS_DIR, label) if rel == "." \
                    else os.path.join(POSTS_DIR, label, rel)
                os.makedirs(out_dir, exist_ok=True)
                fm = ("---\n"
                      f'title: "{yaml_escape(stem)}"\n'
                      f"date: {get_date(src_path)}\n"
                      "draft: false\n"
                      "---\n\n")
                with open(os.path.join(out_dir, fn), "w", encoding="utf-8") as f:
                    f.write(fm + body)
                total += 1

    # 给每个分类目录补 _index.md（让 PaperMod 把它当独立分类页）
    sections = 0
    for dp, _, _ in os.walk(POSTS_DIR):
        if dp == POSTS_DIR:
            continue
        idxf = os.path.join(dp, "_index.md")
        if not os.path.exists(idxf):
            name = os.path.basename(dp)
            with open(idxf, "w", encoding="utf-8") as f:
                f.write("---\n" f'title: "{yaml_escape(name)}"\n' "---\n")
            sections += 1

    print(f"完成：{total} 篇文章，{sections} 个分类页 -> {POSTS_DIR}")
    if missing:
        print(f"\n没找到的图片（{len(missing)} 个），引用已保留，请手动检查：")
        for x in missing:
            print("  - " + x)


if __name__ == "__main__":
    main()
