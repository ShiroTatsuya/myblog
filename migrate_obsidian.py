#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Obsidian 笔记迁移到 Hugo (PaperMod 主题)。

它会做三件事：
  1. 给每篇 .md 补上 YAML front matter（title 取自文件名，date 取自文件修改时间）
  2. 把 ![[图片.png]] 转成 Hugo 标准写法，并把图片复制到 static/images/<来源>/ 下
  3. 把少量 [[双链]] 转成纯文字（[[笔记|别名]] 取别名，[[笔记]] 取笔记名）

原始 Obsidian 文件不会被改动，所有结果都写进 Hugo 项目里，跑坏了也不影响你的笔记库。

用法：把本文件放在任意位置，确认下面“改这里”的路径无误后，在命令行运行：
    python migrate_obsidian.py
"""

import os
import re
import shutil
import datetime
import urllib.parse

# ===================== 改这里 =====================
# 你的 Hugo 项目根目录
HUGO_PROJECT = r"C:\Users\ShiroX\myblog"

# 每个来源：label 是给图片分的子文件夹名（随意，用英文即可，避免重名覆盖）
#          md_dir 是放 .md 的文件夹；img_dir 是它对应的 Images 文件夹
SOURCES = [
    {
        "label":   "knowledge",
        "md_dir":  r"E:\Obsidian-vault\obsidian-vault\02_LIBRARY\R_Resources\Knowledge",
        "img_dir": r"E:\Obsidian-vault\obsidian-vault\02_LIBRARY\R_Resources\Knowledge\Images",
    },
    {
        "label":   "methods",
        "md_dir":  r"E:\Obsidian-vault\obsidian-vault\02_LIBRARY\A_Areas\TRPG\Methods",
        "img_dir": r"E:\Obsidian-vault\obsidian-vault\02_LIBRARY\A_Areas\TRPG\Methods\Images",
    },
]

# 日期取值方式："mtime" = 文件修改时间，"ctime" = 创建时间（Windows 上可用）
DATE_SOURCE = "mtime"
# =================================================

POSTS_DIR  = os.path.join(HUGO_PROJECT, "content", "posts")
STATIC_IMG = os.path.join(HUGO_PROJECT, "static", "images")

EMBED_RE = re.compile(r'!\[\[([^\]\|]+?)(?:\|[^\]]*)?\]\]')          # ![[img.png]] / ![[img.png|300]]
LINK_RE  = re.compile(r'(?<!\!)\[\[([^\]\|]+?)(?:\|([^\]]*))?\]\]')  # [[note]] / [[note|alias]]


def yaml_escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


def get_date(path):
    ts = os.path.getctime(path) if DATE_SOURCE == "ctime" else os.path.getmtime(path)
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")


used_names = set()


def unique_post_name(stem, label):
    """两个来源若有同名 .md，自动追加后缀避免覆盖。"""
    name = stem + ".md"
    if name.lower() not in used_names:
        used_names.add(name.lower())
        return name
    name = f"{stem}-{label}.md"
    i = 2
    while name.lower() in used_names:
        name = f"{stem}-{label}-{i}.md"
        i += 1
    used_names.add(name.lower())
    return name


def main():
    os.makedirs(POSTS_DIR, exist_ok=True)
    total = 0
    missing = []

    for src in SOURCES:
        label, md_dir, img_dir = src["label"], src["md_dir"], src["img_dir"]
        out_img_dir = os.path.join(STATIC_IMG, label)
        os.makedirs(out_img_dir, exist_ok=True)

        if not os.path.isdir(md_dir):
            print(f"[跳过] 找不到目录：{md_dir}")
            continue

        for fn in os.listdir(md_dir):
            if not fn.lower().endswith(".md"):
                continue
            src_path = os.path.join(md_dir, fn)
            if not os.path.isfile(src_path):
                continue
            stem = os.path.splitext(fn)[0]

            with open(src_path, "r", encoding="utf-8") as f:
                body = f.read()

            copied = set()

            def repl_embed(m):
                base = os.path.basename(m.group(1).strip())
                if base not in copied:
                    cand = os.path.join(img_dir, base)
                    if os.path.isfile(cand):
                        shutil.copy2(cand, os.path.join(out_img_dir, base))
                        copied.add(base)
                    else:
                        missing.append(f"{fn}：{base}")
                url = "/images/" + label + "/" + urllib.parse.quote(base)
                return f"![]({url})"

            def repl_link(m):
                note, alias = m.group(1), m.group(2)
                return (alias if alias else note).strip()

            body = EMBED_RE.sub(repl_embed, body)
            body = LINK_RE.sub(repl_link, body)

            front_matter = (
                "---\n"
                f'title: "{yaml_escape(stem)}"\n'
                f"date: {get_date(src_path)}\n"
                "draft: false\n"
                "---\n\n"
            )

            out_name = unique_post_name(stem, label)
            with open(os.path.join(POSTS_DIR, out_name), "w", encoding="utf-8") as f:
                f.write(front_matter + body)
            total += 1

    print(f"完成：共处理 {total} 篇文章 -> {POSTS_DIR}")
    if missing:
        print(f"\n以下图片在对应 Images 文件夹里没找到（{len(missing)} 个），引用已保留，请手动检查：")
        for x in missing:
            print("  - " + x)


if __name__ == "__main__":
    main()
