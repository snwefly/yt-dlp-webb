#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 extractor 导入问题的脚本
"""

import os
import sys
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def fix_extractors():
    """修复有问题的 extractor 导入"""

    extractor_dir = "/app/yt_dlp/extractor"
    extractors_file = os.path.join(extractor_dir, "_extractors.py")

    if not os.path.exists(extractors_file):
        logger.warning(f"_extractors.py 文件不存在: {extractors_file}")
        return False

    # 有问题的 extractor 列表（当前为空，screencastify 是正常的提取器）
    problematic_extractors = [
        # 'screencastify',  # 移除，这是正常的 yt-dlp 提取器
        # 可以根据需要添加其他有问题的 extractor
    ]

    logger.info("🔧 开始修复 extractor 导入问题...")

    # 备份原文件
    backup_file = extractors_file + ".backup"
    if not os.path.exists(backup_file):
        shutil.copy2(extractors_file, backup_file)
        logger.info(f"✅ 已备份原文件: {backup_file}")

    try:
        # 读取原文件
        with open(extractors_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 修复导入行
        lines = content.split('\n')
        fixed_lines = []
        fixed_count = 0

        for line in lines:
            line_fixed = False
            for extractor in problematic_extractors:
                if f'from .{extractor} import' in line:
                    # 注释掉有问题的导入
                    fixed_line = f"# {line}  # 临时注释以避免导入错误"
                    fixed_lines.append(fixed_line)
                    logger.info(f"🔧 修复导入: {extractor}")
                    fixed_count += 1
                    line_fixed = True
                    break

            if not line_fixed:
                fixed_lines.append(line)

        if fixed_count > 0:
            # 写入修复后的文件
            with open(extractors_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))

            logger.info(f"✅ 已修复 {fixed_count} 个导入问题")
            return True
        else:
            logger.info("ℹ️ 没有发现需要修复的导入问题")
            return True

    except Exception as e:
        logger.error(f"❌ 修复过程出错: {e}")

        # 恢复备份文件
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, extractors_file)
            logger.info("🔄 已恢复备份文件")

        return False

def test_import():
    """测试 yt-dlp 导入"""
    logger.info("🧪 测试 yt-dlp 导入...")

    try:
        import yt_dlp

        # 获取版本信息（使用正确的方式）
        version = 'Unknown'
        try:
            # 官方正确方式：从 yt_dlp.version 导入
            from yt_dlp.version import __version__
            version = __version__
        except ImportError:
            try:
                # 备用方式1：通过 yt_dlp.version 模块
                version = yt_dlp.version.__version__
            except AttributeError:
                try:
                    # 备用方式2：直接从 yt_dlp（某些旧版本）
                    version = yt_dlp.__version__
                except AttributeError:
                    pass

        logger.info(f"✅ yt-dlp 导入成功，版本: {version}")

        # 测试创建实例
        try:
            ydl = yt_dlp.YoutubeDL({
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
            })
            logger.info("✅ YoutubeDL 实例创建成功")
            ydl.close()
            return True
        except Exception as e:
            logger.warning(f"⚠️ YoutubeDL 实例创建失败: {e}")
            return False

    except ImportError as e:
        logger.error(f"❌ yt-dlp 导入失败: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始检查 yt-dlp 状态...")

    # 由于 problematic_extractors 列表为空，这个脚本主要用于测试 yt-dlp 导入
    # 测试当前状态
    if test_import():
        logger.info("🎉 yt-dlp 工作正常")
        return 0
    else:
        logger.warning("⚠️ yt-dlp 导入测试失败，但这可能是正常的")
        logger.info("ℹ️ 应用启动时会重新尝试初始化 yt-dlp")
        # 不返回错误码，避免阻止应用启动
        return 0

if __name__ == "__main__":
    sys.exit(main())
