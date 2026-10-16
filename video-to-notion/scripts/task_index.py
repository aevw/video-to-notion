#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Safely register one video processing batch without scanning personal files."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import time
from urllib.parse import urlsplit, parse_qsl

VERSION = "0.5.0"


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("JSON 包含重复键，停止写入")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("数据路径须为相对 data 根目录的非空路径")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value == ".":
        raise ValueError("数据路径不能越出 data 目录")


def validate(entry):
    fields = {"task_id", "run_id", "title", "source", "started_at", "ended_at", "status", "mode", "task_dir", "paths", "skill_version"}
    if not isinstance(entry, dict) or set(entry) != fields:
        raise ValueError("条目字段不符合 schema 1；请按材料指南填写完整条目")
    for key in ("task_id", "run_id"):
        if not isinstance(entry[key], str) or not re.fullmatch(r"[A-Za-z0-9_-]+", entry[key]):
            raise ValueError("task_id/run_id 只能包含字母、数字、下划线和连字符")
    for key in ("title", "skill_version"):
        if entry[key] is not None and not isinstance(entry[key], str):
            raise ValueError(f"{key} 应为文本或 null")
    times = {}
    for key in ("started_at", "ended_at"):
        value = entry[key]
        if value is not None:
            moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                raise ValueError("处理时间必须包含时区；未知用 null")
            times[key] = moment
    if len(times) == 2 and times["ended_at"] < times["started_at"]:
        raise ValueError("结束时间不能早于开始时间")
    if entry["status"] not in ("in_progress", "complete", "partial", "failed") or entry["mode"] not in ("extract", "reuse", "backfill"):
        raise ValueError("status 或 mode 无效")
    if entry["status"] == "in_progress" and entry["ended_at"] is not None:
        raise ValueError("处理中条目不能填写结束时间")
    if entry["mode"] != "backfill" and (entry["started_at"] is None or entry["skill_version"] is None or (entry["status"] != "in_progress" and entry["ended_at"] is None)):
        raise ValueError("新批次须记录实际时间及实际加载的 Skill 版本")
    relative(entry["task_dir"])
    paths = entry["paths"]
    if not isinstance(paths, dict) or set(paths) != {"sources", "derived", "article", "record"}:
        raise ValueError("paths 须包含 sources/derived/article/record")
    for key, value in paths.items():
        values = value if key in ("sources", "derived") else [value]
        if not isinstance(values, list):
            raise ValueError("sources/derived 须为路径数组")
        for item in values:
            if item is not None:
                relative(item)
    source = entry["source"]
    if not isinstance(source, dict) or set(source) != {"platform", "url", "local_path", "video_id", "part"}:
        raise ValueError("source 字段不完整")
    if any(value is not None and not isinstance(value, str) for value in source.values()):
        raise ValueError("source 值须为文本或 null")
    if source["url"]:
        url = urlsplit(source["url"])
        if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.fragment:
            raise ValueError("请使用不含凭据、fragment 的来源 URL")
        if any(key not in {"v", "p", "t", "start"} for key, _ in parse_qsl(url.query, keep_blank_values=True)):
            raise ValueError("来源 URL 只保留 v/p/t/start；先移除跟踪、签名和授权参数")


def update(data, entry, timeout=10):
    validate(entry)
    data = Path(data).expanduser().resolve()
    data.mkdir(parents=True, exist_ok=True)
    index, lock = data / "index.json", data / ".index.lock"
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise ValueError("索引正在写入或遗留锁存在；确认没有写入进程后再处理 .index.lock，不自动抢锁")
            time.sleep(0.05)
    temporary = None
    try:
        if index.is_symlink():
            raise ValueError("索引是符号链接，停止写入")
        content = read_json(index) if index.exists() else {"schema_version": 1, "runs": []}
        if not isinstance(content, dict) or set(content) != {"schema_version", "runs"} or type(content["schema_version"]) is not int or content["schema_version"] != 1 or not isinstance(content["runs"], list):
            raise ValueError("未知或损坏的索引结构，保留原文件")
        seen = set()
        for old in content["runs"]:
            validate(old)
            identity = (old["task_id"], old["run_id"])
            if identity in seen:
                raise ValueError("索引包含重复批次，保留原文件")
            seen.add(identity)
            if old["task_id"] == entry["task_id"] and (old["source"] != entry["source"] or old["task_dir"] != entry["task_dir"]):
                raise ValueError("同一任务的来源或目录不一致，不能覆盖旧记录")
        match = next((i for i, old in enumerate(content["runs"]) if (old["task_id"], old["run_id"]) == (entry["task_id"], entry["run_id"])), None)
        if match is not None:
            old = content["runs"][match]
            if old == entry:
                return index
            if old["status"] != "in_progress" or any(old[key] != entry[key] for key in ("started_at", "skill_version", "mode")):
                raise ValueError("已结束批次不可改写，或批次起始信息不一致；重试/复用请新建 run_id")
            content["runs"][match] = entry
        else:
            content["runs"].append(entry)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=data, prefix=".index-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(content, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, index)
        return index
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description="在锁内原子更新 data/index.json；不扫描目录、不改材料。")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--data-dir", type=Path, required=True, help="实际 data 根目录；测试必须使用临时目录")
    parser.add_argument("--entry", type=Path, required=True, help="按材料指南填写的单个 UTF-8 JSON 条目")
    args = parser.parse_args()
    print(f"索引已更新：{update(args.data_dir, read_json(args.entry))}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"索引未更新：{exc}", file=sys.stderr)
        sys.exit(1)
